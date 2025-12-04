import logging
from typing import List, Optional, Dict, Tuple
import torch
from chromadb.api.models.Collection import Collection
from transformers import PreTrainedModel, PreTrainedTokenizer

from .bm25_retrieval import BM25Retriever

logger = logging.getLogger("rag")

def dpr_search_ids(
    query: str,
    q_encoder: PreTrainedModel,
    tokenizer: PreTrainedTokenizer,
    pooler,
    chroma_collection: Collection,
    device: str = "cuda",
    max_length: int = 512,
    top_k: int = 30,
) -> List[Tuple[str, float]]:

    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    q_encoder = q_encoder.to(device)
    q_encoder.eval()

    if pooler is not None and hasattr(pooler, "to"):
        pooler.to(device)

    q_batch = tokenizer(
        [query],
        padding=True,
        truncation=True,
        max_length=max_length,
        return_tensors="pt",
    )
    q_batch = {k: v.to(device) for k, v in q_batch.items()}

    with torch.no_grad():
        outputs = q_encoder(
            input_ids=q_batch["input_ids"],
            attention_mask=q_batch["attention_mask"],
            token_type_ids=q_batch.get("token_type_ids", None),
        )

    if pooler is not None:
        embedding = pooler(q_batch["attention_mask"], outputs).cpu().numpy()
    else:
        embedding = outputs.last_hidden_state[:, 0, :].cpu().numpy()

    chroma_res = chroma_collection.query(
        query_embeddings=[embedding[0].tolist()],
        n_results=top_k,
        include=["distances", "metadatas"],  
    )

    logger.info(f"[DPR] Chroma query result ids: {chroma_res.get('ids')}")
    logger.info(f"[DPR] Chroma query result distances: {chroma_res.get('distances')}")

    results: List[Tuple[str, float]] = []
    if chroma_res["ids"]:
        ids = chroma_res["ids"][0]
        dists = chroma_res["distances"][0]
        metadatas = chroma_res.get("metadatas", [[]])[0]

        logger.info(
            f"[DPR] Raw Chroma results for query='{query[:50]}...': {len(ids)}개"
        )

        for i, doc_id in enumerate(ids):
            score = 1.0 - dists[i]
            meta = metadatas[i] if i < len(metadatas) else {}
            title = (meta or {}).get("title") or (meta or {}).get("doc_title") or ""
            logger.info(
                f"[DPR][{i + 1}] id={doc_id}, score={score:.4f}, title='{title}'"
            )
            results.append((doc_id, score))

    logger.info(f"[DPR] Retrieved {len(results)} document IDs")
    return results


def hybrid_search_ids(
    query: str,
    q_encoder: PreTrainedModel,
    tokenizer: PreTrainedTokenizer,
    pooler,
    chroma_collection: Collection,
    bm25_retriever: Optional[BM25Retriever] = None,
    device: str = "cuda",
    max_length: int = 512,
    dense_top_k: int = 30,
    bm25_top_k: int = 30,
    final_top_k: int = 10,
    alpha: float = 0.3,
) -> List[str]:
    dpr_results = dpr_search_ids(
        query,
        q_encoder,
        tokenizer,
        pooler,
        chroma_collection,
        device,
        max_length,
        dense_top_k,
    )
    logger.info(f"[DPR] Retrieved {len(dpr_results)} document IDs")

    bm25_results: List[Tuple[str, float]] = []
    if bm25_retriever is not None and bm25_top_k > 0:
        bm25_results = bm25_retriever.search_with_scores(query, top_k=bm25_top_k)
        logger.info(f"[BM25] Retrieved {len(bm25_results)} document IDs")

    rrf_scores: Dict[str, float] = {}
    rrf_k = 60

    if dpr_results:
        for rank, (doc_id, _) in enumerate(dpr_results):
            if doc_id not in rrf_scores:
                rrf_scores[doc_id] = 0.0

            rrf_scores[doc_id] += alpha * (1 / (rrf_k + rank + 1))

    if bm25_results:
        for rank, (doc_id, _) in enumerate(bm25_results):
            if doc_id not in rrf_scores:
                rrf_scores[doc_id] = 0.0

            rrf_scores[doc_id] += (1 - alpha) * (1 / (rrf_k + rank + 1))

    final_scores = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

    top_doc_ids = [doc_id for doc_id, _ in final_scores[:final_top_k]]

    logger.info(f"[HYBRID] Final {len(top_doc_ids)} document IDs selected (RRF Method)")
    for rank, (doc_id, score) in enumerate(final_scores[:final_top_k], start=1):
        logger.info(f"[HYBRID][{rank}] id={doc_id}, rrf_score={score:.6f}")

    return top_doc_ids


def search_documents(
    query: str,
    q_encoder: PreTrainedModel,
    tokenizer: PreTrainedTokenizer,
    pooler,
    chroma_collection: Collection,
    bm25_retriever: Optional[BM25Retriever] = None,
    device: str = "cpu",
    max_length: int = 512,
    dense_top_k: int = 30,
    bm25_top_k: int = 30,
    final_top_k: int = 10,
    dense_weight: float = 1.0,
    bm25_weight: float = 0.5,
    rrf_k: int = 10,
) -> List[str]:
    logger.warning("search_documents is deprecated. Use hybrid_search_ids instead.")

    alpha = dense_weight / (dense_weight + bm25_weight)

    return hybrid_search_ids(
        query,
        q_encoder,
        tokenizer,
        pooler,
        chroma_collection,
        bm25_retriever,
        device,
        max_length,
        dense_top_k,
        bm25_top_k,
        final_top_k,
        alpha,
    )
