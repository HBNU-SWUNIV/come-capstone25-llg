
import fitz
import os
import sys
from pathlib import Path
from typing import List, Dict, Any

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.logger import setup_logger

class TableProcessor:
    def __init__(self, dpi: int = 300):
        self.dpi = dpi
        self.counter = 0
        self.logger = setup_logger(self.__class__.__name__)
    
    def process_tables(self, page: fitz.Page, pdf_name: str, output_dir: str, page_num: int) -> tuple:
        from core.validator import is_valid_table

        content_list = []
        elements = []
        table_rects = []
        
        tables = page.find_tables()
        
        for table_idx, table in enumerate(tables):
            try:
                table_rect = table.bbox
                table_data = table.extract()

                if not is_valid_table(table_data):
                    continue 

                table_rects.append(table_rect)
                
                # 테이블 이미지 파일명을 custom_id 형식으로 변경
                table_img_filename = f"{pdf_name}_{self.counter:04d}_table.png"
                table_img_path = os.path.join(output_dir, table_img_filename)
                
                pix = page.get_pixmap(clip=table_rect, dpi=self.dpi)
                pix.save(table_img_path)

                table_text = "\n".join(["\t".join([str(cell) if cell else "" for cell in row]) for row in table_data])
                table_token = f"[TABLE_{pdf_name}_{self.counter:04d}]"

                content_list.append({
                    "type": "table",
                    "content": table_text,
                    "token": table_token,
                    "image_path": table_img_path,
                    "custom_id": f"{pdf_name}_{self.counter:04d}",
                    "metadata": {
                        "page": page_num + 1,
                        "table_index": table_idx,
                        "bbox": table_rect
                    }
                })

                elements.append({
                    "type": "table_token",
                    "content": table_token,
                    "bbox": table_rect,
                    "y": table_rect[1]
                })
                
                self.counter += 1

            except Exception as e:
                self.logger.error(f"Table extract error on page {page_num + 1}, table {table_idx}: {e}")
        
        return content_list, elements, table_rects