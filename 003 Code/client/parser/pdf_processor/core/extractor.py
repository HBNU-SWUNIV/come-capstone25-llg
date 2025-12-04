import fitz
import os
import sys
from pathlib import Path
from typing import List, Dict, Any

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from processors.table_processor import TableProcessor
from processors.image_processor import ImageProcessor
from processors.text_processor import TextProcessor
from core.chunker import TextChunker
from formatters.jsonl_formatter import JSONLFormatter
from utils.logger import setup_logger
from utils.file_utils import FileUtils

class PDFExtractor:
    def __init__(self, chunk_size: int = 1024, dpi: int = 300, overlap_threshold: float = 0.7):
        self.chunk_size = chunk_size
        self.table_processor = TableProcessor(dpi=dpi)
        self.image_processor = ImageProcessor(dpi=dpi)
        self.text_processor = TextProcessor(overlap_threshold=overlap_threshold)
        self.text_chunker = TextChunker()
        self.formatter = JSONLFormatter()
        self.file_utils = FileUtils()
        self.logger = setup_logger(self.__class__.__name__)
    
    def extract_content(self, pdf_path: str, output_dir: str) -> List[Dict[str, Any]]:
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        self.file_utils.ensure_directory(output_dir)
        
        doc = fitz.open(pdf_path)
        content_list = []
        
        pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
        
        pdf_output_dir = os.path.join(output_dir, pdf_name)
        self.file_utils.ensure_directory(pdf_output_dir)
        
        self.table_processor.counter = 0
        self.image_processor.counter = 0
        
        try:
            for page_num in range(len(doc)):
                page = doc[page_num]
                elements = []
                
                table_content, table_elements, table_rects = self.table_processor.process_tables(
                    page, pdf_name, pdf_output_dir, page_num
                )
                content_list.extend(table_content)
                elements.extend(table_elements)
                
                text_elements = self.text_processor.process_text_blocks(page, table_rects)
                elements.extend(text_elements)
                
                image_content, image_elements = self.image_processor.process_images(
                    page, doc, pdf_name, pdf_output_dir, page_num
                )
                content_list.extend(image_content)
                elements.extend(image_elements)
                
                elements.sort(key=lambda x: x["y"])
                
                page_text_parts = []
                for element in elements:
                    if element["type"] == "text":
                        page_text_parts.append(element["content"])
                    elif element["type"] in ["table_token", "image_token"]:
                        page_text_parts.append(element["content"])
                
                if page_text_parts:
                    full_text = " ".join(page_text_parts)
                    text_chunks = self.text_chunker.chunk_text(full_text, self.chunk_size)
                    for chunk_idx, chunk in enumerate(text_chunks):
                        content_list.append({
                            "type": "text",
                            "content": chunk,
                            "metadata": {
                                "page": page_num + 1,
                                "chunk_index": chunk_idx,
                                "source": pdf_path,
                                "pdf_name": pdf_name
                            }
                        })
        
        finally:
            doc.close()
        
        return content_list