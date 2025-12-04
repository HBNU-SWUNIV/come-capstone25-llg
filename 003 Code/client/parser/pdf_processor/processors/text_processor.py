import fitz
import os
import sys
from pathlib import Path
from typing import List, Dict, Any

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
from utils.logger import setup_logger

class TextProcessor:
    def __init__(self, overlap_threshold: float = 0.7):
        self.overlap_threshold = overlap_threshold
        self.logger = setup_logger(self.__class__.__name__)
    
    def process_text_blocks(self, page: fitz.Page, table_rects: List) -> List[Dict[str, Any]]:
        """테이블/이미지 영역과 겹쳐도 텍스트는 항상 추가한다."""
        elements = []
        
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            if block["type"] != 0:  # 텍스트 블록만 처리
                continue

            block_bbox = fitz.Rect(block["bbox"])
            overlaps_with_table = False
                
            # 👇 이 부분은 이제 '정보용'일 뿐, 필터링에는 안 씀
            for table_rect in table_rects:
                intersection = block_bbox & table_rect
                if intersection:
                    overlap_ratio = intersection.get_area() / block_bbox.get_area()
                    if overlap_ratio > self.overlap_threshold:
                        overlaps_with_table = True
                        break

            # ❌ 기존에는 여기서 overlaps_with_table이면 통째로 버렸음
            # if not overlaps_with_table:

            block_text = ""
            for line in block["lines"]:
                for span in line["spans"]:
                    block_text += span["text"]

            if block_text.strip():
                elements.append({
                    "type": "text",          # 기존과 동일하게 text
                    "content": block_text,
                    "bbox": block["bbox"],
                    "y": block["bbox"][1],
                    # 필요하면 여기서 overlaps_with_table을 metadata로 넣어도 됨
                    # "in_table_or_image": overlaps_with_table,
                })
        
        return elements
