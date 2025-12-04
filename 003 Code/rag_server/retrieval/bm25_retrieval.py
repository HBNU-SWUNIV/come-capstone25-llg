"""
Pyserini BM25 검색 래퍼 클래스
기존 BM25Retriever 인터페이스 유지하면서 Pyserini 사용
"""
import logging
from typing import List, Tuple, Optional
from pyserini.search.lucene import LuceneSearcher

logger = logging.getLogger("rag")

class BM25Retriever:
    """Pyserini 기반 BM25 검색기"""
    
    def __init__(self, index_path: str) -> None:
        """
        Args:
            index_path: Pyserini 인덱스 디렉토리 경로
        """
        self.index_path = index_path
        self.searcher = None
        self._initialize_searcher()
    
    def _initialize_searcher(self) -> None:
        """Pyserini searcher 초기화"""
        try:
            self.searcher = LuceneSearcher(self.index_path)
            logger.info(f"BM25 index loaded from {self.index_path}")
            logger.info(f"Index contains {self.searcher.num_docs} documents")
        except Exception as e:
            logger.error(f"Failed to load BM25 index: {e}")
            self.searcher = None
    
    def search(self, query: str, top_k: int = 30) -> List[str]:
        """
        문서 ID 리스트 반환 (기존 인터페이스 호환)
        
        Args:
            query: 검색 쿼리
            top_k: 반환할 상위 K개 문서
        
        Returns:
            문서 ID 리스트
        """
        if self.searcher is None:
            logger.warning("BM25 searcher not available")
            return []
        
        try:
            hits = self.searcher.search(query, k=top_k)
            doc_ids = [hit.docid for hit in hits]
            logger.info(f"[BM25] Retrieved {len(doc_ids)} document IDs")
            return doc_ids
        
        except Exception as e:
            logger.error(f"BM25 search error: {e}")
            return []
    
    def search_with_scores(self, query: str, top_k: int = 30) -> List[Tuple[str, float]]:
        """
        문서 ID와 점수 반환
        
        Returns:
            [(doc_id, score), ...] 리스트
        """
        if self.searcher is None:
            logger.warning("BM25 searcher not available")
            return []
        
        try:
            hits = self.searcher.search(query, k=top_k)
            results = [(hit.docid, hit.score) for hit in hits]
            logger.info(f"[BM25] Retrieved {len(results)} documents with scores")
            return results
        
        except Exception as e:
            logger.error(f"BM25 search error: {e}")
            return []
    
    def search_with_metadata(self, query: str, top_k: int = 30) -> List[Tuple[dict, str]]:
        """
        메타데이터와 문서 ID 반환 (기존 인터페이스 호환)
        
        Returns:
            [(metadata_dict, doc_id), ...] 리스트
        """
        results = self.search_with_scores(query, top_k)
        return [
            ({"score": score}, doc_id) 
            for doc_id, score in results
        ]
