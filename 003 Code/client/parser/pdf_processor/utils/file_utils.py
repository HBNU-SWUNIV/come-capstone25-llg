
import os
from typing import Set
from pathlib import Path

class FileUtils:
    @staticmethod
    def get_processed_pdfs(log_file: str) -> Set[str]:
        processed = set()
        if os.path.exists(log_file):
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    processed.add(line.strip())
        return processed
    
    @staticmethod
    def log_processed_pdf(log_file: str, pdf_name: str):
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(pdf_name + "\n")
    
    @staticmethod
    def ensure_directory(directory: str):
        os.makedirs(directory, exist_ok=True)
    
    @staticmethod
    def get_pdf_files(directory: str) -> list:
        return [f for f in os.listdir(directory) if f.lower().endswith(".pdf")]