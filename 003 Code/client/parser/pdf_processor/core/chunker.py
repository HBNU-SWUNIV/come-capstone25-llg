import re
from typing import List, Optional
 
 
class TextChunker:
    def __init__(
        self,
        default_chunk_size: int = 1024,
        overlap_ratio: float = 0.2,
        min_chunk_size: int = 50,
    ):
        self.default_chunk_size = default_chunk_size
        self.overlap_ratio = overlap_ratio
        self.min_chunk_size = min_chunk_size
 
    def _clean_text(self, text: str) -> str:
        if not text:
            return ""
 
        text = re.sub(r"[\u200b-\u200f\u202a-\u202e]", "", text)
        noisy_symbols = r"[■◆●▶▷◀◁▲△▼▽※☆★♥◆◇○●●•▪◦·]"
        text = re.sub(noisy_symbols, " ", text)
        text = re.sub(r"[^\x09\x0A\x0D\x20-\x7E\u00A0-\uD7FF]", " ", text)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n+", "\n", text)
 
        return text.strip()
 
    def _is_meaningful_chunk(self, chunk: str) -> bool:
        if len(chunk) < self.min_chunk_size:
            return False
 
        meaningful_chars = len(re.sub(r"[\d\s\W_]", "", chunk))
        total_chars = len(chunk)
 
        if total_chars == 0:
            return False
 
        if (meaningful_chars / total_chars) < 0.3:
            return False
 
        return True
 
    def _create_chunk_from_splits(
        self, splits: List[str], separator: str, final_chunks: List[str]
    ):
        text = separator.join(splits)
        if text.strip():
            final_chunks.append(text)
 
    def _split_recursively(
        self,
        text: str,
        separators: List[str],
        chunk_size: int,
        overlap_size: int,
        final_chunks: List[str],
    ):
        """
        Recursively splits text using the provided separators hierarchy.
        """
        if not separators or len(text) <= chunk_size:
            final_chunks.append(text)
            return
 
        separator = separators[0]
        next_separators = separators[1:]
 
        if separator == "":
            start = 0
            while start < len(text):
                end = min(start + chunk_size, len(text))
                final_chunks.append(text[start:end])
                start += max(1, chunk_size - overlap_size)
            return
 
        splits = text.split(separator)
        current_doc = []
        current_len = 0
 
        for split in splits:
            split_len = len(split)
 
            if split_len > chunk_size:
                if current_doc:
                    self._create_chunk_from_splits(current_doc, separator, final_chunks)
                    current_doc = []
                    current_len = 0
                self._split_recursively(
                    split, next_separators, chunk_size, overlap_size, final_chunks
                )
                continue
 
            sep_len = len(separator) if current_doc else 0
            if current_len + sep_len + split_len > chunk_size:
                self._create_chunk_from_splits(current_doc, separator, final_chunks)
 
                while current_len > overlap_size and current_doc:
                    removed = current_doc.pop(0)
                    current_len -= len(removed)
                    if current_doc:
                        current_len -= len(separator)
 
            current_doc.append(split)
            current_len += split_len + (len(separator) if len(current_doc) > 1 else 0)
 
        if current_doc:
            self._create_chunk_from_splits(current_doc, separator, final_chunks)
 
    def chunk_text(
        self,
        text: str,
        chunk_size: Optional[int] = None,
        overlap_ratio: Optional[float] = None,
    ) -> List[str]:
        if chunk_size is None:
            chunk_size = self.default_chunk_size
        if overlap_ratio is None:
            overlap_ratio = self.overlap_ratio
 
        text = self._clean_text(text)
        if not text:
            return []
 
        separators = ["\n\n", ". ", " "]
        final_chunks = []
 
        overlap_size = int(chunk_size * overlap_ratio)
        self._split_recursively(
            text, separators, chunk_size, overlap_size, final_chunks
        )
 
        unique_chunks = []
        seen = set()
        for c in final_chunks:
            c = c.strip()
            if c and c not in seen and self._is_meaningful_chunk(c):
                unique_chunks.append(c)
                seen.add(c)
 
        return unique_chunks