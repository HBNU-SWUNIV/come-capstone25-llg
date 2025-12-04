import os
import sys
import json
import argparse
from typing import List

import torch
import numpy as np
from tqdm import tqdm
from chromadb import PersistentClient
from transformers import AutoModel, AutoTokenizer
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent                 # .../rag_server/doc_retrieval/database
PROJECT_ROOT = CURRENT_DIR.parents[1]                         # .../rag_server
DEFAULT_CORPUS_PATH = PROJECT_ROOT / "data" / "corpus.jsonl"  # .../rag_server/data/corpus.jsonl
DEFAULT_CHROMA_DB_DIR = PROJECT_ROOT / "chroma_db"          # .../rag_server/chroma_db_3

PARENT_DIR = CURRENT_DIR.parent                               
sys.path.append(str(PARENT_DIR))

from dpr.model import Pooler


def parse_args():
    parser = argparse.ArgumentParser(
        description="Index JSONL corpus with DPR context encoder into ChromaDB"
    )

    parser.add_argument(
        "--model_dir",
        type=str,
        required=False,
        default="../model/context_encoder",
        help="학습된 DPR context encoder 디렉토리 (AutoModel.from_pretrained 대상)",
    )
    parser.add_argument(
        "--corpus_path",
        type=str,
        default=str(DEFAULT_CORPUS_PATH),
        help=f"인덱싱할 JSONL 코퍼스 경로 (default: {DEFAULT_CORPUS_PATH})",
    )
    parser.add_argument(
        "--chroma_db_dir",
        type=str,
        default=str(DEFAULT_CHROMA_DB_DIR),
        help=f"Chroma PersistentClient 디렉토리 (default: {DEFAULT_CHROMA_DB_DIR})",
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

    return parser.parse_args()


def iter_corpus(jsonl_path: str):
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)

            text = obj.get("text", "").strip()
            if not text:
                continue

            doc_id = str(obj.get("_id", idx))
            title = obj.get("title", "")

            yield doc_id, title, text


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
        embeddings = pooler(batch["attention_mask"], outputs)  # (B, D)
    else:
        embeddings = outputs.last_hidden_state[:, 0, :]

    embeddings = embeddings.cpu().numpy()
    return embeddings


def main():
    args = parse_args()

    print("=== 설정 ===")
    print(f"Project root     : {PROJECT_ROOT}")
    print(f"Model dir        : {args.model_dir}")
    print(f"Corpus path      : {args.corpus_path}")
    print(f"Chroma DB dir    : {args.chroma_db_dir}")
    print(f"Collection name  : {args.collection_name}")
    print(f"Batch size       : {args.batch_size}")
    print(f"Max length       : {args.max_length}")
    print(f"Device           : {args.device}")
    print(f"Pooler type      : {args.pooler_type}")
    print("================")

    print(">>> Loading DPR context encoder & tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(args.model_dir)
    model = AutoModel.from_pretrained(args.model_dir)
    model.to(args.device)
    model.eval()

    pooler = Pooler(args.pooler_type)

    print(">>> Initializing Chroma PersistentClient...")
    os.makedirs(args.chroma_db_dir, exist_ok=True)
    client = PersistentClient(path=args.chroma_db_dir)
    collection = client.get_or_create_collection(name=args.collection_name)

    print(">>> Current collection size:", collection.count())

    ids_batch: List[str] = []
    titles_batch: List[str] = []
    texts_batch: List[str] = []

    total_docs = 0
    for doc_id, title, text in tqdm(iter_corpus(args.corpus_path), desc="Reading corpus"):
        ids_batch.append(doc_id)
        titles_batch.append(title)
        texts_batch.append(text)
        total_docs += 1

        if len(ids_batch) >= args.batch_size:
            embeddings = encode_batch(
                titles_batch, texts_batch, tokenizer, model, pooler, args.max_length, args.device
            )

            collection.add(
                ids=ids_batch,
                documents=texts_batch,
                metadatas=[{"title": t} for t in titles_batch],
                embeddings=embeddings.tolist(),
            )

            ids_batch, titles_batch, texts_batch = [], [], []

    if ids_batch:
        embeddings = encode_batch(
            titles_batch, texts_batch, tokenizer, model, pooler, args.max_length, args.device
        )
        collection.add(
            ids=ids_batch,
            documents=texts_batch,
            metadatas=[{"title": t} for t in titles_batch],
            embeddings=embeddings.tolist(),
        )

    print(">>> Total docs processed :", total_docs)
    print(">>> Final collection size:", collection.count())
    print(">>> Done building Chroma index from JSONL corpus.")


if __name__ == "__main__":
    main()
