import json
from collections import defaultdict

# 원본 valid.json 로드
with open("../data/qa.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# question 기준 병합
merged = defaultdict(lambda: {"question": "", "answers": "", "positive": [], "answer_idx": set()})

for item in data:
    q = item["question"].strip()
    merged[q]["question"] = q
    merged[q]["answers"] = item["answers"]  # 여러 개가 있어도 어차피 id로 묶여 있음

    # positive 문단 추가 (중복 방지)
    for pos in item["positive"]:
        if pos["idx"] not in [p["idx"] for p in merged[q]["positive"]]:
            merged[q]["positive"].append(pos)
    
    # answer_idx 병합
    merged[q]["answer_idx"].update(item["answer_idx"])

# set → list 변환
final_data = []
for v in merged.values():
    v["answer_idx"] = list(v["answer_idx"])
    final_data.append(v)

# 저장
with open("../data/qa.json", "w", encoding="utf-8") as f:
    json.dump(final_data, f, ensure_ascii=False, indent=2)

print(f"총 쿼리 수 (중복 제거 후): {len(final_data)}")