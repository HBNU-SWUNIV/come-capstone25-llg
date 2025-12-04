import json
 
# 입력 파일 경로
query_path = "../data/queries.jsonl"
corpus_path = "../data/corpus.jsonl"
output_path = "../data/qa_data.json"

# corpus 불러오기 및 original_id 기준으로 묶기
from collections import defaultdict

original_id_to_chunks = defaultdict(list)

with open(corpus_path, "r", encoding="utf-8") as f:
    for line in f:
        doc = json.loads(line)
        original_id = doc.get("_id")
        if original_id:
            original_id_to_chunks[original_id].append({
                "title": doc["title"],
                "text": doc["text"],
                "idx": doc["_id"]
            })

# queries 읽고 DPR 형식으로 변환
dpr_data = []

with open(query_path, "r", encoding="utf-8") as f:
    for line in f:
        query = json.loads(line)
        source_id = query["metadata"]["source"]
        trainee_id = query["metadata"]["trainee"]
        positives = original_id_to_chunks.get(source_id, [])

        if not positives:
            continue  # 매칭되는 청크 없으면 건너뛰기

        entry = {
            "question": query["text"],
            "answers": trainee_id,
            "positive": positives,
            "answer_idx": [p["idx"] for p in positives]
        }

        dpr_data.append(entry)

# 결과 저장 (JSON 형식으로 저장)
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(dpr_data, f, ensure_ascii=False, indent=2)

print(f"✅ 변환 완료! 총 {len(dpr_data)}개의 쿼리가 저장되었습니다 → {output_path}")
