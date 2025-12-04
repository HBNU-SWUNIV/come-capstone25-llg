import logging
from typing import List, Tuple, Optional
from pyserini.search.lucene import LuceneSearcher

logger = logging.getLogger("rag")

class BM25Retriever:
    def __init__(self, index_path: str) -> None:
        self.index_path = index_path
        self.searcher = None
        self._initialize_searcher()
    
    def _initialize_searcher(self) -> None:
        try:
            self.searcher = LuceneSearcher(self.index_path)
            logger.info(f"BM25 index loaded from {self.index_path}")
            logger.info(f"Index contains {self.searcher.num_docs} documents")
        except Exception as e:
            logger.error(f"Failed to load BM25 index: {e}")
            self.searcher = None
    
    def search(self, query: str, top_k: int = 30) -> List[str]:
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
        results = self.search_with_scores(query, top_k)
        return [
            ({"score": score}, doc_id) 
            for doc_id, score in results
        ]
