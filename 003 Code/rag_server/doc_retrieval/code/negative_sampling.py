from rank_bm25 import BM25Okapi
from tqdm import tqdm
import string, json

def preprocess_text(text):
    """텍스트 전처리: 소문자화 및 구두점 제거"""
    text = text.lower()
    text = text.translate(str.maketrans('', '', string.punctuation))
    return text.split()

def add_hard_negatives_with_bm25(dpr_data, all_corpus, top_n=5):
    corpus_texts = [doc['text'] for doc in all_corpus]
    tokenized_corpus = [preprocess_text(text) for text in corpus_texts]
    bm25 = BM25Okapi(tokenized_corpus)

    for sample in tqdm(dpr_data, desc="Adding hard negatives"):
        # 이미 hard_neg 필드가 존재하면 건너뜀
        if 'hard_neg' in sample and sample['hard_neg']:
            continue

        question = sample['question']
        positive_ids = set(sample['answer_idx'])

        query_tokens = preprocess_text(question)
        scores = bm25.get_scores(query_tokens)
        sorted_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)

        negative_samples = []
        for idx in sorted_indices:
            corpus_doc = all_corpus[idx]
            if corpus_doc['_id'] not in positive_ids:
                negative_samples.append({
                    'text': corpus_doc['text'],
                    'title': corpus_doc['title'],
                    'idx': corpus_doc['_id']
                })
            if len(negative_samples) >= len(positive_ids):
                break

        sample['hard_neg'] = negative_samples

    return dpr_data

def load_data_from_jsonl(jsonl_file):
    with open(jsonl_file, 'r', encoding='utf-8') as f:
        return [json.loads(line) for line in f]

def load_data_from_json(json_file):
    with open(json_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_data_to_json(data, json_file):
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# 사용 예시
corpus_file = '../data/corpus.jsonl'
dpr_data_file = '../data/train.json'
output_file = '../data/train.json'

# 데이터 로드
all_corpus = load_data_from_jsonl(corpus_file)
dpr_data = load_data_from_json(dpr_data_file)

# 하드 네거티브 추가
dpr_data_with_negatives = add_hard_negatives_with_bm25(dpr_data, all_corpus)

# 저장
save_data_to_json(dpr_data_with_negatives, output_file)

# 결과 예시 출력
print(json.dumps(dpr_data_with_negatives[0], ensure_ascii=False, indent=2))