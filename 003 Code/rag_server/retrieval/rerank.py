from typing import List

import torch
from transformers import PreTrainedModel, PreTrainedTokenizer


def rerank(
    query: str,
    docs: List[str],
    model: PreTrainedModel,
    tokenizer: PreTrainedTokenizer,
    top_k: int = 3,
    device: str = "cuda",
) -> List[str]:

    if not docs:
        return docs

    model.to(device)
    model.eval()

    pairs = [[query, d] for d in docs]

    with torch.no_grad():
        encoded = tokenizer(
            pairs,
            padding=True,
            truncation=True,
            return_tensors="pt",
        ).to(device)

        outputs = model(**encoded)
        logits = outputs.logits.squeeze(-1) 
        scores = logits.detach().cpu().numpy()

    sorted_idx = scores.argsort()[::-1][:top_k]
    reranked_docs = [docs[i] for i in sorted_idx]
    return reranked_docs
