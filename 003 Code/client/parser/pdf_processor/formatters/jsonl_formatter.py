
from typing import List, Dict, Any
import re
from utils.logger import setup_logger

class JSONLFormatter:
    def __init__(self):
        self.logger = setup_logger(self.__class__.__name__)
    
    def format_for_jsonl(self, content_list: List[Dict[str, Any]], pdf_name: str) -> List[Dict[str, Any]]:
        table_map = {}
        for item in content_list:
            if item["type"] == "table":
                token = item["token"]
                table_text = item["content"].strip()
                table_map[token] = f"[SOT]\n{table_text}\n[EOT]"

        formatted = []
        chunk_counter = {} 
        
        for item in content_list:
            if item["type"] == "table":
                continue
            elif item["type"] == "text":
                text = item["content"]
                for token, table_markup in table_map.items():
                    if token in text:
                        text = text.replace(token, table_markup)
            else:
                text = item["content"]
            
            text = self.clean_text(text)
            
            item_type = item["type"]
            if item_type not in chunk_counter:
                chunk_counter[item_type] = 0
            else:
                chunk_counter[item_type] += 1
            
            custom_id = f"{pdf_name}_{chunk_counter[item_type]:04d}"
            
            formatted.append({
                "_id": custom_id,
                "title": f"{pdf_name}_text", 
                "text": text,
            })
        return formatted
    
    @staticmethod
    def clean_text(text: str) -> str:
        text = re.sub(r"[ \t]{2,}", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()