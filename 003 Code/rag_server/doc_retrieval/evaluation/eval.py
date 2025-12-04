import torch
import json
import argparse
import numpy as np
import faiss
from transformers import AutoTokenizer, AutoModel
from sklearn.metrics.pairwise import cosine_similarity
import os
import pickle


def recall_at_k(preds, answers, k):
    return len(set(preds[:k]) & set(answers)) / len(set(answers))


def dcg_at_k(relevance_scores):
    return sum(rel / np.log2(i + 2) for i, rel in enumerate(relevance_scores))


def ndcg_at_k(preds, answers, k):
    preds_k = preds[:k]
    relevance_scores = [1 if pid in answers else 0 for pid in preds_k]
    dcg = dcg_at_k(relevance_scores)
    idcg = dcg_at_k(sorted(relevance_scores, reverse=True))
    return dcg / idcg if idcg > 0 else 0


class CrossEncoderScorer:
    def __init__(self, model_path, device='cuda'):
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModel.from_pretrained(model_path).to(device)
        self.classifier = torch.nn.Linear(self.model.config.hidden_size, 1).to(device)
        self.classifier.load_state_dict(torch.load(f"{model_path}/classifier.pt", map_location=device))
        self.device = device

    def score(self, question, docs, max_length=512, batch_size=32):
        scores = []
        print(f"[CrossEncoder] Scoring {len(docs)} documents for question: {question[:50]}...")
        for i in range(0, len(docs), batch_size):
            batch_docs = docs[i:i+batch_size]
            inputs = self.tokenizer(
                [question] * len(batch_docs),
                batch_docs,
                padding=True,
                truncation=True,
                max_length=max_length,
                return_tensors='pt'
            ).to(self.device)

            with torch.no_grad():
                outputs = self.model(**inputs)
                pooled = outputs.pooler_output if hasattr(outputs, "pooler_output") else outputs.last_hidden_state[:, 0]
                batch_scores = self.classifier(pooled).squeeze(-1).cpu().tolist()

            scores.extend(batch_scores if isinstance(batch_scores, list) else [batch_scores])
        return scores


class DPRScorer:
    def __init__(self, q_encoder_path, p_encoder_path, device='cuda'):
        self.q_encoder = AutoModel.from_pretrained(q_encoder_path).to(device)
        self.p_encoder = AutoModel.from_pretrained(p_encoder_path).to(device)
        self.tokenizer = AutoTokenizer.from_pretrained(q_encoder_path)
        self.device = device

    def encode(self, texts, batch_size=64, use_passage_encoder=False):
        model = self.p_encoder if use_passage_encoder else self.q_encoder
        embeddings = []

        print(f"[DPR] Encoding {'passages' if use_passage_encoder else 'questions'}: {len(texts)}")

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            inputs = self.tokenizer(batch, padding=True, truncation=True, return_tensors='pt', max_length=512).to(self.device)
            with torch.no_grad():
                output = model(**inputs)
                emb = output.last_hidden_state[:, 0].cpu().numpy()
                embeddings.append(emb)

        return np.vstack(embeddings)

    def score(self, question, doc_embeddings):
        q_vec = self.encode([question], use_passage_encoder=False)
        sims = cosine_similarity(q_vec, doc_embeddings).flatten()
        return sims.tolist()


class FAISSScorer:
    def __init__(self, dpr_scorer, pickle_path):
        self.dpr_scorer = dpr_scorer

        print(f"[FAISS] Loading FAISS index and doc IDs from pickle: {pickle_path}")
        with open(pickle_path, 'rb') as f:
            data = pickle.load(f)

        self.index = data['faiss_index']
        self.doc_ids = data['text_index']

    def score(self, question, top_k=100):
        q_vec = self.dpr_scorer.encode([question], use_passage_encoder=False).astype(np.float32)
        D, I = self.index.search(q_vec, top_k)
        return [self.doc_ids[i] for i in I[0]]


def load_eval_data(path, full_document_data_path=None):
    with open(path) as f:
        data = json.load(f)

    questions, answer_ids = [], []
    context_dict = {}

    for item in data:
        q = item["question"]
        a = item["answer_idx"]
        for pos in item["positive"]:
            context_dict[pos["idx"]] = {
                "idx": pos["idx"],
                "title": pos["title"],
                "text": pos["text"]
            }
        questions.append(q)
        answer_ids.append(a if isinstance(a, list) else [a])

    if full_document_data_path:
        with open(full_document_data_path, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                doc = json.loads(line)
                if doc["_id"] not in context_dict:
                    context_dict[doc["_id"]] = {
                        "idx": doc["_id"],
                        "title": doc["title"],
                        "text": doc["text"]
                    }

    contexts = list(context_dict.values())
    return questions, contexts, answer_ids


def evaluate_with_scores(get_scores_fn, questions, answer_ids, top_k_values):
    for k in top_k_values:
        recalls, ndcgs = [], []
        for q, answers in zip(questions, answer_ids):
            ranked_ids = get_scores_fn(q, k)
            recalls.append(recall_at_k(ranked_ids, answers, k))
            ndcgs.append(ndcg_at_k(ranked_ids, answers, k))

        print(f"Recall@{k}: {np.mean(recalls):.4f}")
        print(f"NDCG@{k}:  {np.mean(ndcgs):.4f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_path", type=str, required=True)
    parser.add_argument("--full_document_data_path", type=str, required=True)
    parser.add_argument("--model_type", type=str, choices=["cross", "dpr"], required=True)
    parser.add_argument("--model_path", type=str, required=True)
    parser.add_argument("--passage_encoder_path", type=str)
    parser.add_argument("--device", type=str, default="cuda")
    parser.add_argument("--top_k", type=str, default="1,5,10,20,50,100")
    parser.add_argument("--use_faiss", action="store_true")
    parser.add_argument("--faiss_index_path", type=str)
    args = parser.parse_args()

    top_k_values = list(map(int, args.top_k.split(',')))

    print("[INFO] Loading data...")
    questions, contexts, answer_ids = load_eval_data(args.data_path, args.full_document_data_path)
    doc_ids = [ctx["idx"] for ctx in contexts]
    doc_texts = [f"{ctx['title']} {ctx['text']}" for ctx in contexts]
    print(f"[INFO] Loaded {len(doc_texts)} documents.")
    print(f"[INFO] Loaded {len(questions)} questions.")

    if args.model_type == "cross":
        print("[INFO] Using CrossEncoder.")
        model = CrossEncoderScorer(args.model_path, device=args.device)
        get_scores_fn = lambda q, k: [
            doc_ids[i] for i in np.argsort(model.score(q, doc_texts))[::-1][:k]
        ]
    else:
        print("[INFO] Using DPR.")
        model = DPRScorer(args.model_path, args.passage_encoder_path, device=args.device)

        if args.use_faiss:
            if not args.faiss_index_path:
                raise ValueError("`--faiss_index_path` must be provided with --use_faiss.")
            faiss_scorer = FAISSScorer(model, pickle_path=args.faiss_index_path)
            get_scores_fn = lambda q, k: faiss_scorer.score(q, top_k=k)
        else:
            print("[INFO] Encoding document embeddings for DPR (no FAISS)...")
            doc_embeddings = model.encode(doc_texts, use_passage_encoder=True)

            def get_scores_fn(q, k):
                sims = model.score(q, doc_embeddings)
                top_indices = np.argsort(sims)[::-1][:k]
                return [doc_ids[i] for i in top_indices]

    print("[INFO] Starting evaluation...")
    evaluate_with_scores(get_scores_fn, questions, answer_ids, top_k_values)