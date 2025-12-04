import os
import sys
import json
import argparse
from pathlib import Path
from typing import List
import psycopg2
from tqdm import tqdm

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parents[1]           # /app
DEFAULT_INDEX_DIR = PROJECT_ROOT / "pyserini_index"  

PARENT_DIR = CURRENT_DIR.parent
sys.path.append(str(PARENT_DIR))


# --------------------------------------------
# 1. CONFIG LOAD
# --------------------------------------------
def load_config(path="config.json"):
    path = Path(path)
    if not path.is_absolute():
        base_dir = Path(__file__).resolve().parent  # /app/doc_retrieval/database
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
# 3. EXPORT CORPUS TO JSONL
# --------------------------------------------

def export_corpus_to_jsonl(conn, output_path):
    """
    Text 테이블에서 문서를 읽어 Pyserini 형식의 JSONL로 저장
    Pyserini 형식: {"id": "doc_id", "contents": "text", "metadata": {...}}
    """
    print(f">>> Exporting corpus to {output_path}")
    
    document_count = 0
    
    with open(output_path, "w", encoding="utf-8") as f:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, pdf_id, content, chunk_index, metadata
                FROM "text"
                ORDER BY pdf_id, chunk_index
            """)
            
            for row in tqdm(cur, desc="Exporting documents"):
                text_id, pdf_id, content, chunk_index, metadata = row
                
                if not content or not content.strip():
                    continue
                
                # Pyserini 형식의 문서
                doc = {
                    "id": str(text_id),
                    "contents": content,
                    "pdf_id": str(pdf_id),
                    "chunk_index": chunk_index,
                }
                
                # metadata가 있으면 추가
                if metadata:
                    doc["metadata"] = metadata
                
                f.write(json.dumps(doc, ensure_ascii=False) + "\n")
                document_count += 1
    
    print(f">>> Exported {document_count} documents")
    return document_count


# --------------------------------------------
# 4. BUILD PYSERINI INDEX
# --------------------------------------------

def build_pyserini_index(jsonl_path, index_dir, language="korean"):
    import subprocess
    import sys
    import shutil

    print(f">>> Building Pyserini index at {index_dir}")

    index_path = Path(index_dir)
    temp_path = Path(jsonl_path).parent

    # ✅ 인덱스 디렉토리 안의 내용만 삭제 (마운트 포인트 자체는 유지)
    if index_path.exists():
        print(f">>> Clearing existing index dir {index_dir}")
        for child in index_path.iterdir():
            try:
                if child.is_file() or child.is_symlink():
                    child.unlink()
                elif child.is_dir():
                    shutil.rmtree(child)
            except Exception as e:
                print(f">>> Warning: failed to remove {child}: {e}")
    else:
        index_path.mkdir(parents=True, exist_ok=True)

    # 혹시 위에서 존재했으면 mkdir 생략되고, 없었으면 여기서 생성됨
    index_path.mkdir(parents=True, exist_ok=True)

    # temp 디렉토리가 있는지 확인
    if not temp_path.exists() or not Path(jsonl_path).exists():
        raise RuntimeError(f"JSONL file not found at {jsonl_path}")

    # ✅ 현재 파이썬 실행 파일로 pyserini 호출 (환경 확실히)
    cmd = [
        sys.executable, "-m", "pyserini.index.lucene",
        "--collection", "JsonCollection",
        "--input", str(temp_path),
        "--index", str(index_dir),
        "--generator", "DefaultLuceneDocumentGenerator",
        "--threads", "4",
    ]

    # 한국어의 경우 CJK analyzer 사용
    if language == "korean":
        cmd.extend(["--language", "ko"])

    print(f">>> Running command: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(">>> Pyserini index built successfully")

        # 인덱스 통계 출력
        from pyserini.search.lucene import LuceneSearcher
        try:
            searcher = LuceneSearcher(str(index_dir))
            print(f">>> Index statistics:")
            print(f"    Total documents: {searcher.num_docs}")
        except Exception as e:
            print(f">>> Could not load index stats: {e}")

    except subprocess.CalledProcessError as e:
        print(f">>> Error building index:")
        print(f">>> stdout: {e.stdout}")
        print(f">>> stderr: {e.stderr}")
        raise

# --------------------------------------------
# 5. MAIN
# --------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Build Pyserini BM25 index from PostgreSQL Text table"
    )
    
    parser.add_argument(
        "--config",
        type=str,
        default="config.json",
        help="DB 정보가 담긴 config.json 경로",
    )
    parser.add_argument(
        "--index_dir",
        type=str,
        default=str(DEFAULT_INDEX_DIR),
        help="Pyserini 인덱스를 저장할 디렉토리",
    )
    parser.add_argument(
        "--language",
        type=str,
        default="korean",
        choices=["korean", "english"],
        help="문서 언어 (korean/english)",
    )
    parser.add_argument(
        "--temp_dir",
        type=str,
        default=None,
        help="JSONL 파일을 저장할 임시 디렉토리 (기본: index_dir/temp)",
    )
    
    args = parser.parse_args()
    
    # 임시 디렉토리를 시스템 temp에 생성 (완료 후 자동 삭제)
    import tempfile
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)
        jsonl_path = temp_dir / "corpus.jsonl"
        
        # Load config
        cfg = load_config(args.config)
        
        print("=== 설정 ===")
        print(f"Project root     : {PROJECT_ROOT}")
        print(f"Config file      : {args.config}")
        print(f"Index dir        : {args.index_dir}")
        print(f"Language         : {args.language}")
        print(f"Temp JSONL path  : {jsonl_path}")
        print("================")
        
        # Connect to DB
        print(">>> Connecting to DB...")
        conn = connect_db(cfg)
        
        try:
            # Step 1: Export corpus to JSONL
            doc_count = export_corpus_to_jsonl(conn, jsonl_path)
            
            if doc_count == 0:
                print(">>> No documents found in DB. Exiting.")
                return
            
            # Step 2: Build Pyserini index
            build_pyserini_index(jsonl_path, args.index_dir, args.language)
            
            print(">>> Done!")
            print(f">>> Index saved at: {args.index_dir}")
            print(f">>> Temp JSONL will be automatically deleted")
            
        finally:
            conn.close()
            print(">>> DB connection closed")
        
        # temp_dir는 with 블록 종료 시 자동 삭제됨


if __name__ == "__main__":
    main()