set -e

echo "[ENTRYPOINT] Waiting a bit for DB & Chroma to be ready..."
sleep 10

echo "[ENTRYPOINT] Running DB -> Chroma indexing..."
python /app/doc_retrieval/database/db_to_chroma.py
echo "[ENTRYPOINT] DB -> Chroma indexing done."

echo "[ENTRYPOINT] Building Pyserini BM25 index from DB..."
python /app/doc_retrieval/database/pyserini_bm25.py
echo "[ENTRYPOINT] Pyserini index build done."

echo "[ENTRYPOINT] Starting RAG server..."
exec python /app/main.py
