import os
from pathlib import Path
from chromadb import PersistentClient

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parents[2] 
CHROMA_DB_DIR = PROJECT_ROOT / "chroma_db"

client = PersistentClient(path=str(CHROMA_DB_DIR))
collection = client.get_collection("corpus")

print("Collection count:", collection.count())

peek = collection.peek(3)  # 앞에서 3개만
print("Sample IDs     :", peek["ids"])
print("Sample metadata:", peek["metadatas"])
print("Sample docs    :", [d[:80] + "..." for d in peek["documents"]])
