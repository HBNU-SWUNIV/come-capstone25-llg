#!/usr/bin/env bash
set -e

echo "[ENTRYPOINT] Waiting a bit for DB & Chroma to be ready..."
sleep 10

# 1) DPR + Chroma 인덱싱 (항상 실행)
echo "[ENTRYPOINT] Running DB -> Chroma indexing..."
python /app/doc_retrieval/database/db_to_chroma.py
echo "[ENTRYPOINT] DB -> Chroma indexing done."

# 2) Pyserini BM25 인덱스 빌드 (항상 실행)
echo "[ENTRYPOINT] Building Pyserini BM25 index from DB..."
python /app/doc_retrieval/database/pyserini_bm25.py
echo "[ENTRYPOINT] Pyserini index build done."

echo "[ENTRYPOINT] Starting RAG server..."
exec python /app/main.py
