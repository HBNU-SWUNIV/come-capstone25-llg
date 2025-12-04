import logging
import sys
import json
import os
from pathlib import Path
from dotenv import load_dotenv
import re
from typing import List, Dict
import base64
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

from typing import Optional, List, Dict
import torch
import uvicorn
import psycopg2
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from chromadb import HttpClient
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from config import load_api_key
from prompts import system_prompt
from models.generate_answer import generate_answer
from models.load_models_data import load_models_and_data

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR
DOC_RETRIEVAL_DIR = CURRENT_DIR / "doc_retrieval"
sys.path.append(str(DOC_RETRIEVAL_DIR))

from dpr.model import Pooler
from retrieval.bm25_retrieval import BM25Retriever
from retrieval.dpr_retrieval import hybrid_search_ids
from retrieval.rerank import rerank


# ============================================
# 경로 설정
# ============================================
CHROMA_URL = os.getenv("CHROMA_URL", "http://chromadb:8000")  # 환경 변수 설정
CHROMA_COLLECTION_NAME = "corpus"
CONFIG_PATH = PROJECT_ROOT / "doc_retrieval" / "database" / "config.json"
PYSERINI_INDEX_DIR = "/app/pyserini_index"
# ============================================
# 로깅 설정
# ============================================
LOGGER_NAME = "rag"
logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(LOGGER_NAME)
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
logger.info(f"Using device: {DEVICE}")

# ============================================
# DB 설정
# ============================================
# def load_db_config():
#     """환경변수 또는 config.json에서 DB 설정 로드"""
#     if os.getenv("DATABASE_HOST"):
#         return {
#             "host": os.getenv("DATABASE_HOST", "db"),
#             "port": int(os.getenv("DATABASE_PORT", "5432")),
#             "dbname": os.getenv("DATABASE_NAME", "postgres"),
#             "user": os.getenv("DATABASE_USER", "admin"),
#             "password": os.getenv("DATABASE_PASSWORD", ""),
#         }

#     with open(CONFIG_PATH, "r", encoding="utf-8") as f:
#         config = json.load(f)
#     return config["database"]


def load_db_config():
    """
    RAG 서버는 Docker 컨테이너(rag) 안에서만 돌아가므로
    무조건 환경변수만 사용해서 DB에 접속한다.
    (config.json은 host에서 돌리는 스크립트(db_to_chroma.py) 전용)
    """
    db = {
        "host": os.getenv("DATABASE_HOST", "db"),  # 기본 db
        "port": int(os.getenv("DATABASE_PORT", "5432")),  # 컨테이너 내부 포트
        "dbname": os.getenv("DATABASE_NAME", "kilab"),  # 기본 kilab
        "user": os.getenv("DATABASE_USER", "kilab"),
        "password": os.getenv("DATABASE_PASSWORD", "kilab1234"),
    }
    logger.info(
        f"DB 설정 로드 - host={db['host']}, port={db['port']}, dbname={db['dbname']}, user={db['user']}"
    )
    return db


db_config = load_db_config()
db_conn = None


def get_db_connection():
    """DB 연결 가져오기"""
    global db_conn
    if db_conn is None or db_conn.closed:
        db_conn = psycopg2.connect(
            host=db_config["host"],
            port=db_config.get("port", 5432),
            dbname=db_config["dbname"],
            user=db_config["user"],
            password=db_config["password"],
        )
        logger.info("DB 연결 성공")
    return db_conn


def extract_image_tokens(text: str) -> List[str]:
    if not text:
        return []
    matches = re.findall(r"\[([^\]]+)\]", text)
    return matches

def fetch_images_by_ids(tokens: List[str]) -> List[Dict]:
    """
    이미지 토큰 리스트에서 TABLE_..._NNNN 형식을 파싱해
    image.id와 매칭되는 ID로 변환한 뒤 DB에서 실제 이미지를 조회한다.

    tokens 예:
      ['TABLE_2026_한밭대학교_수시모집요강_0000', 'TABLE_2026_한밭대학교_수시모집요강_0001', ...]
    image.id 예:
      '2026_한밭대학교_수시모집요강_img_0.png'
    """
    if not tokens:
        return []

    # 한글 + 언더스코어 포함 전체를 pdf_name으로, 마지막 숫자 부분을 count로 잡는다
    # 예: TABLE_2026_한밭대학교_수시모집요강_0001
    #      -> pdf_name='2026_한밭대학교_수시모집요강', count='0001'
    pattern = r"^TABLE_(.+)_(\d+)$"
    image_ids: List[str] = []

    for token in tokens:
        m = re.match(pattern, token)
        if not m:
            # TABLE_로 시작하지만 형식이 다른 경우를 디버깅하고 싶으면 아래 로그 사용
            logger.debug(f"이미지 토큰 패턴 불일치: {token}")
            continue

        pdf_name, count = m.groups()

        try:
            # '0001' -> 1 로 변환 (DB에는 _img_1.png 형태일 가능성이 높음)
            idx = int(count)
        except ValueError:
            logger.warning(f"이미지 인덱스 파싱 실패: token={token}, count={count}")
            continue

        image_id = f"{pdf_name}_img_{idx}.png"
        image_ids.append(image_id)

    if not image_ids:
        logger.info("이미지 토큰에서 변환된 image_ids가 없어 조회를 생략합니다.")
        return []

    logger.info(f"이미지 조회용 ID 목록: {image_ids}")

    # DB에서 이미지 조회
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        query = """
            SELECT id, image_data, image_index
            FROM image
            WHERE id = ANY(%s)
        """
        cursor.execute(query, (image_ids,))
        results = cursor.fetchall()

        images: List[Dict] = []
        for row in results:
            images.append(
                {
                    "id": row[0],
                    "index": row[2],
                    "base64": base64.b64encode(row[1]).decode("utf-8"),
                }
            )
        logger.info(f"이미지 조회 완료: {len(images)}개 매칭")
        return images

    except Exception as e:
        logger.error(f"이미지 조회 오류: {e}")
        return []
    finally:
        cursor.close()

def fetch_documents_from_db(doc_ids: List[str]) -> Dict[str, str]:
    """
    DB에서 문서 ID로 실제 텍스트 조회
    Returns:
        {doc_id: content} 딕셔너리
    """
    if not doc_ids:
        logger.info("not doc_ids!!!! not doc_ids!!!! not doc_ids!!!!")
        return {}

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        query = "SELECT id, content FROM text WHERE id::text = ANY(%s)"
        cursor.execute(query, (doc_ids,))
        results = cursor.fetchall()

        doc_contents = {str(row[0]): row[1] for row in results}
        logger.info(f"DB에서 {len(doc_contents)}개 문서 조회 완료")
        return doc_contents

    except Exception as e:
        logger.error(f"DB 조회 오류: {e}")
        return {}
    finally:
        cursor.close()


# ============================================
# 인덱스 초기화
# ============================================
# ChromaDB
import re

match = re.match(r"https?://([^:]+):(\d+)", CHROMA_URL)

if match:
    chroma_host = match.group(1)  # 'chromadb'
    chroma_port = int(match.group(2))  # 8000
else:
    chroma_host = "chromadb"
    chroma_port = 8000

try:
    chroma_client = HttpClient(host=chroma_host, port=chroma_port)
    chroma_collection = chroma_client.get_or_create_collection(CHROMA_COLLECTION_NAME)
    logger.info(f"ChromaDB 서버 연결 성공: {CHROMA_URL}")

    try:
        doc_count = chroma_collection.count()
        logger.info(
            f"Chroma collection '{CHROMA_COLLECTION_NAME}' document count = {doc_count}"
        )
    except Exception as e:
        logger.error(f"Chroma collection count 확인 중 오류: {e}")

except Exception as e:
    logger.error(f"ChromaDB 서버 연결 오류: {e}")
    sys.exit(1)


_retrieval_models_cache = {
    "consultant": None,
    "default": None,
}


def get_retrieval_models(is_consultant_mode: bool):
    """
    load_models_and_data(is_consultant_mode)를 한 번만 호출하고
    이후에는 캐시된 tokenizer, q_encoder를 반환
    """
    key = "consultant" if is_consultant_mode else "default"
    if _retrieval_models_cache[key] is None:
        logger.info(f"Loading DPR models for mode={key}")
        tokenizer, q_encoder = load_models_and_data(is_consultant_mode)
        _retrieval_models_cache[key] = (tokenizer, q_encoder)
    else:
        tokenizer, q_encoder = _retrieval_models_cache[key]
    return tokenizer, q_encoder


# BM25 (Pyserini)
bm25_retriever = BM25Retriever(PYSERINI_INDEX_DIR)

# Pooler
pooler = Pooler("cls")

# Reranker
rerank_model_name = "cross-encoder/ms-marco-MiniLM-L-6-v2"
rerank_tokenizer = AutoTokenizer.from_pretrained(rerank_model_name)
rerank_model = AutoModelForSequenceClassification.from_pretrained(rerank_model_name).to(DEVICE)

# ============================================
# FastAPI 앱
# ============================================
app = FastAPI(title="RAG API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RAGRequest(BaseModel):
    query: str
    is_consultant_mode: Optional[bool] = Field(default=False, alias="isConsultantMode")
    model_config = {"populate_by_name": True}

class RAGResponse(BaseModel):
    answer: str
    images: List = []


# ============================================
# RAG 엔드포인트
# ============================================
@app.post("/rag", response_model=RAGResponse)
def rag_generate(request: RAGRequest):
    query = request.query
    is_consultant_mode = request.is_consultant_mode

    logger.info(
        f"RAG 요청 - 쿼리: {query[:50]}"
    )

    try:
        tokenizer, q_encoder = get_retrieval_models(is_consultant_mode)

        logger.info("Hybrid 검색 (DPR + BM25) 시작")
        doc_ids = hybrid_search_ids(
            query=query,
            q_encoder=q_encoder,
            tokenizer=tokenizer,
            pooler=pooler,
            chroma_collection=chroma_collection,
            bm25_retriever=bm25_retriever,
            device=DEVICE,
            max_length=512,
            dense_top_k=30,
            bm25_top_k=30,
            final_top_k=10,
            alpha=0.5,
        )
        logger.info(f"Hybrid search returned {len(doc_ids)} document IDs: {doc_ids}")

        # 3) DB에서 실제 텍스트 가져오기
        doc_contents = fetch_documents_from_db(doc_ids)

        # 검색 결과 문서 로그 (ID + preview)
        for rank, doc_id in enumerate(doc_ids, start=1):
            content = doc_contents.get(doc_id, "[내용 없음]")
            preview = content.replace("\n", " ")[:] if content else "[빈 문서]"
            logger.info(
                f"[RAG][DB][{rank}] id={doc_id}, len={len(content) if content else 0}, preview='{preview}'\n ======================== \n"
            )

        docs = [doc_contents.get(doc_id, "[내용 없음]") for doc_id in doc_ids]
        logger.info(f"Fetched {len(docs)} docs from DB")

        # 4) Reranking (top 3 정도만 context에 사용)
        if docs:
            logger.info("Reranking 시작")
            reranked_docs = rerank(
                query,
                docs,
                rerank_model,
                rerank_tokenizer,
                top_k=3,
                device=DEVICE,
            )
            for rank, d in enumerate(reranked_docs, start=1):
                preview = d.replace("\n", " ")[:200]
                logger.info(f"[RAG][RERANK][{rank}] preview='{preview}'")
            logger.info(f"Reranking 완료 - top {len(reranked_docs)} docs 사용")
        else:
            logger.warning("검색 결과가 없어 Reranking 생략")
            reranked_docs = []

        # 5) Context 구성
        if reranked_docs:
            context = "\n\n--- 다음 문서 ---\n\n".join(reranked_docs)
        else:
            # 검색 실패 시에도 LLM이 최소한 일반 답변은 하도록 빈 컨텍스트 처리
            context = "[검색 결과 없음]\n\n"

        # 이미지 토큰 추출 + 이미지 조회 (1~5 단계)

        all_image_tokens = set()

        # reranked_docs 는 이미 context용 문서 3개만 선정된 상태
        for doc in reranked_docs:
            tokens = extract_image_tokens(doc)
            all_image_tokens.update(tokens)

        logger.info(f"총 이미지 토큰 추출: {all_image_tokens}")

        # DB 조회
        images = fetch_images_by_ids(list(all_image_tokens))
        logger.info(f"DB에서 {len(images)}개 이미지 조회됨")

        # 6) 프롬프트 생성
        prompt = system_prompt(
            is_consultant_mode=is_consultant_mode,
            query=query,
            context=context,
        )

        # 7) 답변 생성
        logger.info("답변 생성을 시작합니다.")
        response_content = generate_answer(prompt)

        logger.info("RAG 응답 생성 완료")
        return RAGResponse(
            answer=response_content,
            images=images,
        )

    except Exception as e:
        logger.error(f"RAG 처리 중 오류: {e}")
        import traceback

        logger.error(f"스택 트레이스: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"RAG 처리 오류: {str(e)}")

@app.on_event("shutdown")
def shutdown_event():
    """서버 종료 시 DB 연결 정리"""
    global db_conn
    if db_conn and not db_conn.closed:
        db_conn.close()
        logger.info("DB 연결 종료")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=False)
