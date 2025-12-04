import fitz
import os
import sys
from pathlib import Path
from typing import List, Dict, Any

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
from utils.logger import setup_logger

class ImageProcessor:
    def __init__(self, dpi: int = 300):
        self.dpi = dpi
        self.counter = 0
        self.logger = setup_logger(self.__class__.__name__)
    
    def process_images(self, page: fitz.Page, doc: fitz.Document, pdf_name: str, output_dir: str, page_num: int) -> tuple:
        content_list = []
        elements = []
        
        images = page.get_images(full=True)
        for img_idx, img in enumerate(images):
            try:
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]
                
                # 이미지 파일명을 custom_id 형식으로 변경
                image_filename = f"{pdf_name}_{self.counter:04d}_image.{image_ext}"
                image_path = os.path.join(output_dir, image_filename)
                
                with open(image_path, "wb") as f:
                    f.write(image_bytes)
                
                img_info = page.get_image_bbox(img)
                img_rect = img_info[1] if img_info and isinstance(img_info, tuple) and len(img_info) > 1 else None

                if isinstance(img_rect, fitz.Rect):
                    # 이미지 영역 파일명도 custom_id 형식으로 변경
                    img_area_filename = f"{pdf_name}_{self.counter:04d}_image_area.png"
                    img_area_path = os.path.join(output_dir, img_area_filename)
                    
                    pix = page.get_pixmap(clip=img_rect, dpi=self.dpi)
                    pix.save(img_area_path)

                    content_list.append({
                        "type": "image",
                        "content": image_path,
                        "image_area_path": img_area_path,
                        "custom_id": f"{pdf_name}_{self.counter:04d}",
                        "metadata": {
                            "page": page_num + 1,
                            "image_index": img_idx,
                            "bbox": list(img_rect)
                        }
                    })

                    image_token = f"[IMAGE_{pdf_name}_{self.counter:04d}]"
                    elements.append({
                        "type": "image_token",
                        "content": image_token,
                        "bbox": img_rect,
                        "y": img_rect[1]
                    })
                    
                    self.counter += 1
                    
            except Exception as e:
                self.logger.error(f"Image extract error on page {page_num + 1}, image {img_idx}: {e}")
        
        return content_list, elements