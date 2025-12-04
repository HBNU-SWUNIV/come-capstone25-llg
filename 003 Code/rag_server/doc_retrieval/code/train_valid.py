import json
import random
from collections import defaultdict

# 하나의 파일 경로
file_path = '../data/qa.json'

# 데이터 로드
with open(file_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

# 중복 제거 (question + positive 기준)
seen = set()
unique_data = []
for item in data:
    q = item['question'].strip()

    # positive 문서 내 text만 추출해서 하나의 문자열로 합침
    pos_chunks = []
    for p in item['positive']:
        if isinstance(p, dict) and 'text' in p:
            pos_chunks.append(p['text'].strip())
        elif isinstance(p, str):
            pos_chunks.append(p.strip())

    pos = ' '.join(pos_chunks)
    key = (q, pos)

    if key not in seen:
        seen.add(key)
        unique_data.append(item)

# 질문 기준으로 그룹화
question_groups = defaultdict(list)
for item in unique_data:
    question_groups[item['question'].strip()].append(item)

# 고유 질문 리스트 추출 후 셔플
all_questions = list(question_groups.keys())
random.seed(42)
random.shuffle(all_questions)

# 분할 인덱스 계산
total = len(all_questions)
train_end = int(total * 0.8)
valid_end = int(total * 0.9)

train_questions = set(all_questions[:train_end])
valid_questions = set(all_questions[train_end:valid_end])
test_questions = set(all_questions[valid_end:])

# 데이터 분할
train_data = []
valid_data = []
test_data = []

for q in train_questions:
    train_data.extend(question_groups[q])
for q in valid_questions:
    valid_data.extend(question_groups[q])
for q in test_questions:
    test_data.extend(question_groups[q])

# 저장
with open('../data/train.json', 'w', encoding='utf-8') as f:
    json.dump(train_data, f, ensure_ascii=False, indent=2)

with open('/../data/valid.json', 'w', encoding='utf-8') as f:
    json.dump(valid_data, f, ensure_ascii=False, indent=2)

with open('../data/test.json', 'w', encoding='utf-8') as f:
    json.dump(test_data, f, ensure_ascii=False, indent=2)

print(f"총 고유 질문 수: {len(all_questions)}")
print(f"Train: {len(train_data)} / Valid: {len(valid_data)} / Test: {len(test_data)}")