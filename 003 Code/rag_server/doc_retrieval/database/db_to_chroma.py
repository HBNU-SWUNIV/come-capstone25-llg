import os
from dotenv import load_dotenv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import sys
import json
import argparse
from typing import List

import torch
import numpy as np
from tqdm import tqdm

# from chromadb import PersistentClient
from chromadb import HttpClient
from transformers import AutoModel, AutoTokenizer
from pathlib import Path
import psycopg2
import re

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parents[1]
DEFAULT_CHROMA_DB_DIR = PROJECT_ROOT / "chroma_db"

REPO_ROOT = CURRENT_DIR.parents[1]                    
MODEL_DIR_DEFAULT = REPO_ROOT / "models" / "context_encoder"

PARENT_DIR = CURRENT_DIR.parent
sys.path.append(str(PARENT_DIR))

from dpr.model import Pooler


# --------------------------------------------
# 1. CONFIG LOAD
# --------------------------------------------


def load_config(path="config.json"):
    path = Path(path)
    if not path.is_absolute():
        base_dir = Path(__file__).resolve().parent  
        path = base_dir / path

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# --------------------------------------------
# 2. DB CONNECT
# --------------------------------------------


def connect_db(cfg):
    db = cfg["database"]

    host = os.getenv("DATABASE_HOST", db["host"])
    port = int(os.getenv("DATABASE_PORT", db.get("port", 5432)))
    dbname = os.getenv("DATABASE_NAME", db["dbname"])
    user = os.getenv("DATABASE_USER", db["user"])
    password = os.getenv("DATABASE_PASSWORD", db["password"])

    print(f">>> DB 접속 정보: host={host}, port={port}, dbname={dbname}, user={user}")

    conn = psycopg2.connect(
        host=host,
        port=port,
        dbname=dbname,
        user=user,
        password=password,
    )
    print(">>> DB 연결 성공")

    return conn



# --------------------------------------------
# 3. ITERATE CORPUS FROM DB
# --------------------------------------------


def iter_corpus_from_db(conn):
    """
    Text(id, pdf_id, content, chunk_index, metadata)
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, pdf_id, content
            FROM "text"
            ORDER BY pdf_id, chunk_index
        """)

        for row in cur:
            text_id, pdf_id, content = row

            if not content:
                continue

            title = str(pdf_id)
            yield str(text_id), title, content


# --------------------------------------------
# 4. BATCH EMBEDDING
# --------------------------------------------


def encode_batch(
    titles: List[str],
    texts: List[str],
    tokenizer,
    model,
    pooler: Pooler,
    max_length: int,
    device: str,
) -> np.ndarray:
    batch = tokenizer(
        titles,
        texts,
        padding=True,
        truncation=True,
        max_length=max_length,
        return_tensors="pt",
    )

    batch = {k: v.to(device) for k, v in batch.items()}

    with torch.no_grad():
        outputs = model(
            input_ids=batch["input_ids"],
            attention_mask=batch["attention_mask"],
            token_type_ids=batch.get("token_type_ids", None),
        )

    if pooler is not None:
        embeddings = pooler(batch["attention_mask"], outputs)
    else:
        embeddings = outputs.last_hidden_state[:, 0, :]

    return embeddings.cpu().numpy()


# --------------------------------------------
# 5. MAIN
# --------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Index DB Text table with DPR context encoder into ChromaDB"
    )
    parser.add_argument(
        "--model_dir",
        type=str,
        default=str(MODEL_DIR_DEFAULT),
        help="DPR context encoder 모델 디렉토리",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config.json",
        help="DB 정보가 담긴 config.json 경로",
    )
    parser.add_argument(
        "--chroma_db_dir",
        type=str,
        default=str(DEFAULT_CHROMA_DB_DIR),
        help="Chroma PersistentClient 디렉토리",
    )
    parser.add_argument(
        "--collection_name",
        type=str,
        default="corpus",
        help="Chroma 컬렉션 이름",
    )
    parser.add_argument(
        "--batch_size",
        type=int,
        default=64,
        help="임베딩 계산 및 Chroma add 시 배치 크기",
    )
    parser.add_argument(
        "--max_length",
        type=int,
        default=512,
        help="토크나이저 max_length",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cuda" if torch.cuda.is_available() else "cpu",
        help="cuda 또는 cpu",
    )
    parser.add_argument(
        "--pooler_type",
        type=str,
        default="cls",
        help="Pooler 타입 (cls / mean / max)",
    )

    args = parser.parse_args()

    # -----------------------------
    # 모델 경로 / fallback 처리
    # -----------------------------
    requested_model_dir = args.model_dir
    model_path = Path(requested_model_dir)

    if model_path.is_dir():
        resolved_model_id = str(model_path)
        print(f"[MODEL] Using local DPR context encoder at: {resolved_model_id}")
    else:
        # 로컬 디렉토리가 없으면 klue/bert-base로 fallback
        resolved_model_id = "snumin44/biencoder-ko-bert-context"
        print(
            f"[MODEL][WARN] Local model dir not found: {requested_model_dir}\n"
            f"          Falling back to HuggingFace model: {resolved_model_id}"
        )

    # Load config
    cfg = load_config(args.config)

    print("=== 설정 ===")
    print(f"Project root     : {PROJECT_ROOT}")
    print(f"Requested model  : {requested_model_dir}")
    print(f"Resolved model   : {resolved_model_id}")
    print(f"Config file      : {args.config}")
    print(f"Chroma DB dir    : {args.chroma_db_dir}")
    print(f"Collection name  : {args.collection_name}")
    print(f"Batch size       : {args.batch_size}")
    print(f"Max length       : {args.max_length}")
    print(f"Device           : {args.device}")
    print(f"Pooler type      : {args.pooler_type}")
    print("================")

    print(">>> Loading DPR context encoder & tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(resolved_model_id)
    model = AutoModel.from_pretrained(resolved_model_id)
    model.to(args.device)
    model.eval()

    pooler = Pooler(args.pooler_type)

    print(">>> Connecting DB...")
    conn = connect_db(cfg)

    with conn.cursor() as cur:
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        tables = cur.fetchall()
        print("Available tables:", tables)

    # ===========================================

    # print(">>> Initializing Chroma PersistentClient...")
    # os.makedirs(args.chroma_db_dir, exist_ok=True)
    # client = PersistentClient(path=args.chroma_db_dir)
    # collection = client.get_or_create_collection(name=args.collection_name)

    # 호스트에서 실행할 때는 localhost:8000이 기본값
    CHROMA_URL = os.getenv("CHROMA_URL", "http://localhost:8002")
    print(f">>> Connecting to Chroma HttpClient: {CHROMA_URL}")
    match = re.match(r"https?://([^:]+):(\d+)", CHROMA_URL)
    if match:
        chroma_host = match.group(1)  # 'chromadb'
        chroma_port = int(match.group(2))  # 8000
    else:
        chroma_host = "chromadb"
        chroma_port = 8000

    client = HttpClient(host=chroma_host, port=chroma_port)
    # collection = client.get_or_create_collection(name=args.collection_name)

    collection = client.get_or_create_collection(
                    name=args.collection_name,
                    metadata={"hnsw:space": "cosine"}  # 또는 "ip"
                )

    print(">>> Current collection size:", collection.count())
    # ===========================================

    ids_batch = []
    titles_batch = []
    texts_batch = []

    total_docs = 0
    for doc_id, title, text in tqdm(iter_corpus_from_db(conn), desc="Reading DB"):
        ids_batch.append(doc_id)
        titles_batch.append(title)
        texts_batch.append(text)
        total_docs += 1

        if len(ids_batch) >= args.batch_size:
            embeddings = encode_batch(
                titles_batch,
                texts_batch,
                tokenizer,
                model,
                pooler,
                args.max_length,
                args.device,
            )

            collection.add(
                ids=ids_batch,
                documents=texts_batch,
                metadatas=[{"title": t} for t in titles_batch],
                embeddings=embeddings.tolist(),
            )

            ids_batch, titles_batch, texts_batch = [], [], []

    # 남은 배치 처리
    if ids_batch:
        embeddings = encode_batch(
            titles_batch,
            texts_batch,
            tokenizer,
            model,
            pooler,
            args.max_length,
            args.device,
        )

        collection.add(
            ids=ids_batch,
            documents=texts_batch,
            metadatas=[{"title": t} for t in titles_batch],
            embeddings=embeddings.tolist(),
        )

    print(">>> Total docs processed :", total_docs)
    print(">>> Final collection size:", collection.count())
    print(">>> Done building Chroma index from DB Text table.")


if __name__ == "__main__":
    main()
