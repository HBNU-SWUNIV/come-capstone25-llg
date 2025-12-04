import os
import logging
import uvicorn
import time
from typing import Optional, List

from sqlalchemy.orm import Session, joinedload # joinedload 추가
from fastapi import FastAPI, HTTPException, Depends
from database import SessionLocal, init_db, ChatSession, ChatMessage, ChatImage 

from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import openai
import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
from config import load_api_key
from llm_cache import LLMCache
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    init_db()
except Exception as e:
    logger.error(f"DB 초기화 실패 (Docker 연결 대기 중일 수 있음): {e}")

app = FastAPI(title="KILAB Chatbot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://ki-chat:3000", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    api_key = load_api_key()
    openai.api_key = api_key
    logger.info("OpenAI API 키 설정 성공")
except Exception as e:
    logger.error(f"OpenAI API 키 설정 실패: {e}")
    openai.api_key = None

chroma_client = chromadb.Client()
EMBEDDING_MODEL = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")

openai_ef = OpenAIEmbeddingFunction(
    api_key=load_api_key(),
    model_name=EMBEDDING_MODEL,
)

semantic_cache = chroma_client.get_or_create_collection(
    name="semantic_cache",
    embedding_function=openai_ef,
    metadata={"hnsw:space": "cosine"},
)

app.llm_cache = LLMCache(semantic_cache)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class Message(BaseModel):
    role: str
    content: str
    is_consultant_mode: Optional[bool] = Field(default=False, alias="consultantMode")
    model_config = {"populate_by_name": True}

class ChatRequest(BaseModel):
    messages: List[Message]
    session_id: Optional[str] = Field(default=None, alias="sessionId")
    is_consultant_mode: Optional[bool] = Field(default=False, alias="isConsultantMode")
    model_config = {"populate_by_name": True}

class ImageItem(BaseModel):
    id: str
    index: int
    base64: str

class ChatResponse(BaseModel):
    role: str
    content: str
    session_id: str
    images: List[ImageItem] = []

@app.get("/")
async def root():
    return JSONResponse({"message": "KILAB Chatbot API가 실행 중입니다."})

@app.get("/sessions")
async def get_sessions(db: Session = Depends(get_db)):
    sessions = db.query(ChatSession).order_by(ChatSession.created_at.desc()).all()
    result = []
    for s in sessions:
        last_msg = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == s.id)
            .order_by(ChatMessage.created_at.desc())
            .first()
        )
        preview = last_msg.content[:30] + "..." if last_msg else "내용 없음"
        result.append({
            "id": s.id,
            "title": s.title,
            "date": s.created_at.strftime("%m.%d"),
            "preview": preview,
            "isConsultant": s.is_consultant_mode,
        })
    return result

@app.get("/sessions/{session_id}/messages")
async def get_session_messages(session_id: str, db: Session = Depends(get_db)):
    msgs = (
        db.query(ChatMessage)
        .options(joinedload(ChatMessage.images)) 
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    
    result = []
    for m in msgs:
        images_data = []
        for img in m.images:
            images_data.append({
                "id": img.id,
                "index": img.index,
                "base64": img.base64
            })
            
        result.append({
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "consultantMode": False,
            "images": images_data 
        })
        
    return result

@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str, db: Session = Depends(get_db)):
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if session:
        db.delete(session)
        db.commit()
    return {"status": "ok"}

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    logger.info(f"API 호출: {request}")

    try:
        user_messages = [msg for msg in request.messages if msg.role == "user" and msg.content.strip()]
        if not user_messages:
            raise HTTPException(status_code=400, detail="유효한 사용자 메시지가 없습니다")

        last_message = user_messages[-1]
        query = last_message.content
        is_consultant_mode = request.is_consultant_mode or last_message.is_consultant_mode

        session_id = request.session_id
        if not session_id:
            new_session = ChatSession(
                title=query[:20],
                is_consultant_mode=is_consultant_mode,
            )
            db.add(new_session)
            db.commit()
            db.refresh(new_session)
            session_id = new_session.id

        db_user_msg = ChatMessage(session_id=session_id, role="user", content=query)
        db.add(db_user_msg)
        db.commit()

        start_time = time.time()
        answer, images = app.llm_cache.generate(query, is_consultant_mode)
        elapsed_time = time.time() - start_time
        logger.info(f"소요 시간: {elapsed_time:.2f}s")

        db_ai_msg = ChatMessage(session_id=session_id, role="assistant", content=answer)
        db.add(db_ai_msg)
        db.commit()
        db.refresh(db_ai_msg) 

        if images:
            for img in images:
                img_base64 = img.base64 if hasattr(img, 'base64') else img.get('base64')
                img_index = img.index if hasattr(img, 'index') else img.get('index', 0)
                
                db_image = ChatImage(
                    message_id=db_ai_msg.id, 
                    base64=img_base64,
                    index=img_index
                )
                db.add(db_image)
            db.commit() 

        response = ChatResponse(
            role="assistant",
            content=answer,
            session_id=session_id,
            images=images,
        )

        return response

    except Exception as e:
        logger.error(f"오류 발생: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)