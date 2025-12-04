# backend/database.py
import os
import json
from sqlalchemy import create_engine, Column, String, Text, Boolean, DateTime, ForeignKey, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import uuid

# 1. 환경 변수에서 DB URL 가져오기 (Docker 환경 우선)
DATABASE_URL = os.getenv("DATABASE_URL")

# 2. 환경 변수가 없으면 config.json 읽기 (로컬 개발 환경 fallback)
if not DATABASE_URL:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
    
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
            db_cfg = config["database"]
            # localhost 설정
            DATABASE_URL = f"postgresql://{db_cfg['user']}:{db_cfg['password']}@{db_cfg['host']}:{db_cfg['port']}/{db_cfg['dbname']}"
            print(f"⚠️ 환경변수 없음. config.json 로드: {DATABASE_URL}")
    except Exception as e:
        print(f"❌ DB 설정 로드 실패: {e}")
        # 기본값 설정 (혹은 에러 발생)
        DATABASE_URL = "postgresql://kilab:kilab1234@localhost:5432/kilab"

# [호환성 처리] SQLAlchemy 1.4+ 에서는 'postgres://' 대신 'postgresql://'을 사용해야 함
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# 3. 엔진 생성
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- 모델 정의 (동일) ---

class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, default="새로운 채팅")
    created_at = Column(DateTime, default=datetime.now)
    is_consultant_mode = Column(Boolean, default=True)
    
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("chat_sessions.id"))
    role = Column(String)
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    session = relationship("ChatSession", back_populates="messages")
    images = relationship("ChatImage", back_populates="message", cascade="all, delete-orphan")
    
class ChatImage(Base):
    __tablename__ = "chat_images"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    message_id = Column(String, ForeignKey("chat_messages.id")) # 어떤 메시지의 이미지인지
    index = Column(Integer) # 이미지 순서
    base64 = Column(Text)   # 이미지 데이터 (Base64 문자열)
    
    message = relationship("ChatMessage", back_populates="images")
    
def init_db():
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ 데이터베이스 테이블 초기화 완료")
    except Exception as e:
        print(f"❌ 데이터베이스 연결 실패: {e}")