import logging
import requests
from fastapi import HTTPException

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LLMCache:
    def __init__(self, semantic_cache):
        self.cache = {}
        self.semantic_cache = semantic_cache

    def generate(self, query, is_consultant_mode):
        """
        항상 (answer: str, images: List[dict]) 형태로 리턴
        """
        if query in self.cache:
            cached_answer = self.cache[query]
            return cached_answer, []


        similar_docs = self.semantic_cache.query(
            query_texts=[query],
            n_results=1,
        )

        if (
            len(similar_docs["distances"][0]) > 0
            and similar_docs["distances"][0][0] < 0.05
        ):
            cached_answer = similar_docs["metadatas"][0][0]["response"]
            self.cache[query] = cached_answer
            return cached_answer, []

        answer, images = self.response_to_rag(query, is_consultant_mode)

        self.cache[query] = answer
        self.semantic_cache.add(
            documents=[query],
            metadatas=[{"response": answer}],
            ids=[query],
        )

        return answer, images

    def response_to_rag(self, query, is_consultant_mode):
        try:
            response = requests.post(
                "http://rag:8001/rag",
                json={"query": query, "isConsultantMode": is_consultant_mode},
                timeout=120,
            )

            if response.status_code != 200:
                raise Exception(
                    f"RAG API 요청 실패: {response.status_code} {response.text}"
                )

            data = response.json()
            return data["answer"], data.get("images", [])

        except Exception as e:
            logger.error(f"오류 발생: {e}")
            raise HTTPException(status_code=500, detail=str(e))
