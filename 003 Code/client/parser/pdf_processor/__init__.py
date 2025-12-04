
import json
import os
from typing import List, Dict, Any

from .core.extractor import PDFExtractor
from .formatters.jsonl_formatter import JSONLFormatter
from .utils.file_utils import FileUtils
from .utils.logger import setup_logger

class PDFProcessor:
    """PDF 처리기 메인 클래스"""
    
    def __init__(self, chunk_size: int = 1024, dpi: int = 300, overlap_threshold: float = 0.7):
        self.chunk_size = chunk_size
        self.extractor = PDFExtractor(chunk_size, dpi, overlap_threshold)
        self.formatter = JSONLFormatter()
        self.file_utils = FileUtils()
        self.logger = setup_logger(self.__class__.__name__)
    
    def process_pdf(self, pdf_path: str, output_dir: str) -> List[Dict[str, Any]]:
        """단일 PDF 파일을 처리합니다."""
        try:
            content = self.extractor.extract_content(pdf_path, output_dir)
            pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
            formatted_content = self.formatter.format_for_jsonl(content, pdf_name)
            
            self.logger.info(f"Processed {pdf_path}: {len(content)} items extracted")
            return formatted_content
            
        except Exception as e:
            self.logger.error(f"Error processing {pdf_path}: {e}")
            raise
    
    def process_directory(self, pdf_dir: str, output_base_dir: str, jsonl_output_path: str = None):
        """디렉토리의 모든 PDF 파일을 처리합니다."""
        self.file_utils.ensure_directory(output_base_dir)
        
        if jsonl_output_path is None:
            jsonl_output_path = os.path.join(output_base_dir, "all_extracted_data.jsonl")
        
        log_file = os.path.join(output_base_dir, "processed_pdfs.log")
        processed_pdfs = self.file_utils.get_processed_pdfs(log_file)
        
        pdf_files = self.file_utils.get_pdf_files(pdf_dir)
        
        for pdf_file in pdf_files:
            pdf_path = os.path.join(pdf_dir, pdf_file)
            pdf_name = os.path.splitext(pdf_file)[0]
            output_dir = os.path.join(output_base_dir, pdf_name)
            
            # 이미 처리된 PDF 건너뛰기
            if pdf_file in processed_pdfs:
                self.logger.info(f"Skipping already processed PDF: {pdf_file}")
                continue
            
            self.logger.info(f"Processing PDF: {pdf_file}")
            try:
                formatted_content = self.process_pdf(pdf_path, output_dir)
                
                # JSONL 파일에 추가
                with open(jsonl_output_path, "a", encoding="utf-8") as f:
                    for entry in formatted_content:
                        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                
                # 처리된 PDF 로그 기록
                self.file_utils.log_processed_pdf(log_file, pdf_file)
                
            except Exception as e:
                self.logger.error(f"Error processing {pdf_file}: {e}")

# Make PDFProcessor available at package level
__all__ = ['PDFProcessor']