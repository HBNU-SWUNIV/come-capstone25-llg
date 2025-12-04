import json
import re
# def parse_questions(response_text):
#     questions = response_text.strip().split("\n\n")
#     question_dict = {}
#     for q in questions:
#         if q.strip():
#             num, text = q.strip().split(".", 1)
#             question_dict[int(num.strip())] = text.strip()
#     return question_dict
def parse_questions(response_text):
    text = response_text.strip()
    question_dict = {}

    # 숫자. 패턴으로 파싱 (공백 없이 붙은 것도 포함)
    pattern = re.compile(r"(\d+)\.(.*?)(?=\d+\.|$)", re.DOTALL)
    matches = list(pattern.finditer(text))

    # 첫 문장이 번호 없이 시작할 경우
    if matches and matches[0].start() > 0:
        first_question = text[:matches[0].start()].strip()
        if first_question:
            question_dict[1] = first_question

    # 번호 있는 질문 추가
    for match in matches:
        num = int(match.group(1))
        qtext = match.group(2).strip()
        if num in question_dict:
            num += 1  # 중복 방지
        question_dict[num] = qtext

    return question_dict

def generate_queries(data):
    queries = []
    query_id_counter = 1

    for item in data:
        uuid = item["uuid"]
        roles = [uuid] + item["roles"]  # uuid 포함 총 9개
        questions = parse_questions(item["response"])

        for role_id in roles:
            for q_num, q_text in questions.items():
                queries.append({
                    "_id": f"query-{query_id_counter:05d}",
                    "text": q_text,
                    "metadata": {
                        "source": role_id,
                        "trainee" : uuid
                    }
                })
                query_id_counter += 1
    return queries

# 예시 사용법
with open("query_output.json", "r", encoding="utf-8") as f:
    data = json.load(f)

queries = generate_queries(data)

# jsonl로 저장
with open("../data/queries.jsonl", "w", encoding="utf-8") as f:
    for q in queries:
        f.write(json.dumps(q, ensure_ascii=False) + "\n")