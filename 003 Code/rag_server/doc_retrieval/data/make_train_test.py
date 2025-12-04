import os
import json
import random
from typing import List, Dict, Any, Tuple


def load_jsonl(path: str) -> List[Dict[str, Any]]:
    data = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            data.append(json.loads(line))
    return data


def save_jsonl(path: str, data: List[Dict[str, Any]]):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for obj in data:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def save_json(path: str, data: List[Dict[str, Any]]):
    """
    BiEncoderDataset에서 json.load로 바로 읽을 수 있도록
    전체를 하나의 리스트(JSON 배열)로 저장.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def build_doc_dict(corpus: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    doc_id -> {"text": str, "title": str(옵션)}
    """
    doc_dict = {}
    for d in corpus:
        doc_id = d.get("_id")
        if not doc_id:
            continue
        text = d.get("text", "")
        title = d.get("title", "") or d.get("metadata", {}).get("title", "")
        doc_dict[doc_id] = {
            "text": text,
            "title": title,
        }
    return doc_dict


# def split_queries(
#     queries: List[Dict[str, Any]],
#     train_ratio: float = 0.8,
#     dev_ratio: float = 0.1,
#     test_ratio: float = 0.1,
#     seed: int = 42,
# ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:

#     assert abs(train_ratio + dev_ratio + test_ratio - 1.0) < 1e-6

#     random.seed(seed)
#     queries_shuffled = queries[:]
#     random.shuffle(queries_shuffled)

#     n = len(queries_shuffled)
#     n_train = int(n * train_ratio)
#     n_dev = int(n * dev_ratio)

#     train_q = queries_shuffled[:n_train]
#     dev_q = queries_shuffled[n_train:n_train + n_dev]
#     test_q = queries_shuffled[n_train + n_dev:]

#     return train_q, dev_q, test_q

def split_queries_by_doc(
    queries: List[Dict[str, Any]],
    train_ratio: float = 0.8,
    dev_ratio: float = 0.1,
    test_ratio: float = 0.1,
    seed: int = 42,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    같은 positive_doc_id(=metadata.source)를 가지는 쿼리 그룹을
    반드시 같은 split(train/dev/test)에 넣도록 분할.
    """

    assert abs(train_ratio + dev_ratio + test_ratio - 1.0) < 1e-6

    # 1) doc_id -> [query, query, ...] 그룹 만들기
    doc_to_queries: Dict[str, List[Dict[str, Any]]] = {}
    for q in queries:
        meta = q.get("metadata", {})
        doc_id = meta.get("source")
        if not doc_id:
            # source 없는 경우는 일단 건너뛴다 (원하면 따로 모아서 처리)
            continue
        doc_to_queries.setdefault(doc_id, []).append(q)

    doc_ids = list(doc_to_queries.keys())
    random.seed(seed)
    random.shuffle(doc_ids)

    n_docs = len(doc_ids)
    n_train_docs = int(n_docs * train_ratio)
    n_dev_docs = int(n_docs * dev_ratio)

    train_doc_ids = set(doc_ids[:n_train_docs])
    dev_doc_ids = set(doc_ids[n_train_docs:n_train_docs + n_dev_docs])
    test_doc_ids = set(doc_ids[n_train_docs + n_dev_docs:])

    train_q, dev_q, test_q = [], [], []

    for doc_id, q_list in doc_to_queries.items():
        if doc_id in train_doc_ids:
            train_q.extend(q_list)
        elif doc_id in dev_doc_ids:
            dev_q.extend(q_list)
        else:
            test_q.extend(q_list)

    return train_q, dev_q, test_q


def sample_negatives(
    all_doc_ids: List[str],
    positive_doc_id: str,
    num_negatives: int,
) -> List[str]:
    """
    간단한 랜덤 negative 샘플링.
    더 고급 전략(hard negative 등)이 있으면 이후 교체 가능.
    """
    candidate_ids = [d for d in all_doc_ids if d != positive_doc_id]
    if len(candidate_ids) <= num_negatives:
        return candidate_ids

    return random.sample(candidate_ids, num_negatives)


def queries_to_dpr_format(
    queries: List[Dict[str, Any]],
    doc_dict: Dict[str, Dict[str, Any]],
    num_negatives: int = 5,
    seed: int = 42,
) -> List[Dict[str, Any]]:
    """
    DPR 학습/평가용 포맷으로 변환
    출력 포맷 예시:

    {
        "query_id": "q_000001",
        "query": "질문 텍스트",
        "positive_passages": [
            {
                "doc_id": "doc123",
                "title": "타이틀",
                "text": "문서 텍스트 ..."
            }
        ],
        "negative_passages": [
            {
                "doc_id": "doc456",
                "title": "",
                "text": "..."
            },
            ...
        ]
    }
    """
    random.seed(seed)
    all_doc_ids = list(doc_dict.keys())
    dpr_examples = []

    for q in queries:
        qid = q.get("_id")
        qtext = q.get("text", "")
        meta = q.get("metadata", {})
        positive_doc_id = meta.get("source")  # corpus에서의 정답 문서 id

        if not qid or not qtext or not positive_doc_id:
            # 최소 정보 없으면 스킵
            continue

        if positive_doc_id not in doc_dict:
            # corpus에 없는 source라면 스킵
            continue

        pos_doc = doc_dict[positive_doc_id]
        pos_passage = {
            "doc_id": positive_doc_id,
            "title": pos_doc.get("title", ""),
            "text": pos_doc.get("text", ""),
        }

        neg_doc_ids = sample_negatives(all_doc_ids, positive_doc_id, num_negatives)
        neg_passages = []
        for ndid in neg_doc_ids:
            ndoc = doc_dict[ndid]
            neg_passages.append(
                {
                    "doc_id": ndid,
                    "title": ndoc.get("title", ""),
                    "text": ndoc.get("text", ""),
                }
            )

        example = {
            "query_id": qid,
            "query": qtext,
            "positive_passages": [pos_passage],
            "negative_passages": neg_passages,
        }
        dpr_examples.append(example)

    return dpr_examples


# --------- 🔴 여기부터 BiEncoderDataset용 포맷 변환 함수 추가 ---------

def dpr_to_biencoder_train(dpr_examples: List[Dict[str, Any]], max_neg_per_query: int = 5) -> List[Dict[str, Any]]:
    biencoder_samples: List[Dict[str, Any]] = []

    for ex in dpr_examples:
        qtext = ex["query"]
        pos = ex["positive_passages"][0]
        doc_id = pos["doc_id"]

        pos_ctx = {
            "idx": doc_id,
            "title": pos.get("title", ""),
            "text": pos.get("text", ""),
        }

        negs = ex.get("negative_passages", [])[:max_neg_per_query]
        hard_neg_list = [
            {
                "idx": neg["doc_id"],
                "title": neg.get("title", ""),
                "text": neg.get("text", ""),
            }
            for neg in negs
        ]

        sample = {
            "question": qtext,
            "answer_idx": doc_id,   # 🔹 train에도 answer_idx 추가
            "positive": [pos_ctx],
        }
        if hard_neg_list:
            sample["hard_neg"] = hard_neg_list

        biencoder_samples.append(sample)

    return biencoder_samples


def dpr_to_biencoder_valid(dpr_examples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    BiEncoderDataset.load_valid_dataset 에서 기대하는 포맷으로 변환.

    [
      {
        "question": "질문 텍스트",
        "answer_idx": "<정답 passage id>",
        "positive": [
          {"idx": "<정답 passage id>", "title": "...", "text": "..."}
        ]
      },
      ...
    ]
    """
    biencoder_samples: List[Dict[str, Any]] = []

    for ex in dpr_examples:
        qtext = ex["query"]
        pos = ex["positive_passages"][0]
        doc_id = pos["doc_id"]  # 🔴 정답 문서 id

        pos_ctx = {
            "idx": doc_id,
            "title": pos.get("title", ""),
            "text": pos.get("text", ""),
        }

        sample = {
            "question": qtext,
            "answer_idx": doc_id,  # 🔴 정답 passage id를 그대로 저장
            "positive": [pos_ctx],
        }
        biencoder_samples.append(sample)

    return biencoder_samples



# -----------------------------------------------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=str, default="corpus.jsonl")
    parser.add_argument("--queries", type=str, default="queries.jsonl")
    parser.add_argument("--out_dir", type=str, default="/home/kilab_kdh/workspace/doc_retrieval/data")
    parser.add_argument("--num_negatives", type=int, default=3)
    parser.add_argument("--train_ratio", type=float, default=0.8)
    parser.add_argument("--dev_ratio", type=float, default=0.1)
    parser.add_argument("--test_ratio", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    print("Loading corpus...")
    corpus = load_jsonl(args.corpus)
    print("Loading queries...")
    queries = load_jsonl(args.queries)
    print(f"- #corpus: {len(corpus)}")
    print(f"- #queries: {len(queries)}")

    doc_dict = build_doc_dict(corpus)

    # 쿼리 split
    train_q, dev_q, test_q = split_queries_by_doc(
        queries,
        train_ratio=args.train_ratio,
        dev_ratio=args.dev_ratio,
        test_ratio=args.test_ratio,
        seed=args.seed,
    )
    print(
        f"Split queries -> train: {len(train_q)}, dev: {len(dev_q)}, test: {len(test_q)}"
    )

    # DPR 포맷으로 변환
    train_dpr = queries_to_dpr_format(
        train_q, doc_dict, num_negatives=args.num_negatives, seed=args.seed
    )
    dev_dpr = queries_to_dpr_format(
        dev_q, doc_dict, num_negatives=args.num_negatives, seed=args.seed + 1
    )
    test_dpr = queries_to_dpr_format(
        test_q, doc_dict, num_negatives=args.num_negatives, seed=args.seed + 2
    )

    print(
        f"DPR examples -> train: {len(train_dpr)}, dev: {len(dev_dpr)}, test: {len(test_dpr)}"
    )

    # # ---------- 기존 DPR jsonl 저장 ----------
    # os.makedirs(args.out_dir, exist_ok=True)
    save_jsonl(os.path.join(args.out_dir, "dpr_train.jsonl"), train_dpr)
    save_jsonl(os.path.join(args.out_dir, "dpr_dev.jsonl"), dev_dpr)
    save_jsonl(os.path.join(args.out_dir, "dpr_test.jsonl"), test_dpr)

    # # BM25 등에서 바로 쓰기 편하도록 쿼리만 별도 저장 (옵션)
    # save_jsonl(os.path.join(args.out_dir, "train_queries.jsonl"), train_q)
    # save_jsonl(os.path.join(args.out_dir, "dev_queries.jsonl"), dev_q)
    # save_jsonl(os.path.join(args.out_dir, "test_queries.jsonl"), test_q)

    # ----------  BiEncoderDataset용 JSON 추가 저장 ----------
    biencoder_train = dpr_to_biencoder_train(train_dpr)
    biencoder_dev = dpr_to_biencoder_valid(dev_dpr)
    biencoder_test = dpr_to_biencoder_valid(test_dpr)

    print(
        f"BiEncoder train samples: {len(biencoder_train)}, "
        f"dev: {len(biencoder_dev)}, test: {len(biencoder_test)}"
    )

    save_json(os.path.join(args.out_dir, "biencoder_train.json"), biencoder_train)
    save_json(os.path.join(args.out_dir, "biencoder_dev.json"), biencoder_dev)
    save_json(os.path.join(args.out_dir, "biencoder_test.json"), biencoder_test)

    print(f"Saved DPR & BiEncoder data to {args.out_dir}")


if __name__ == "__main__":
    main()
