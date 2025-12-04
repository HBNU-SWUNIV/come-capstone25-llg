import pandas as pd
import json
import random
from collections import defaultdict

# 파일 경로
CSV_FILE = "clusters.csv"
PASSAGE_FILE = "passage_final.json"
OUTPUT_FILE = "query_batch.jsonl"

# 1. 파일 불러오기
df = pd.read_csv(CSV_FILE)
with open(PASSAGE_FILE, "r", encoding="utf-8") as f:
    passage_data = json.load(f)

# 2. trainee_info 구성
trainee_info = defaultdict(dict)

for entry in passage_data["passage"]:
    uuid = entry["uuid"]
    trainee = entry["trainee"]

    styles = set()
    for d in trainee.get("favoriteStyle", []):
        for k, v in d.items():
            styles.add(f"{k}:{v}")

    entertainments = set()
    feedbacks = []  # 리스트로 피드백 누적

    for c in entry.get("content", []):
        entertainments.update(c.get("recommendEntertain", []))
        fb = c.get("feedback")
        if fb:
            if isinstance(fb, list):
                feedbacks.extend(fb)
            else:
                feedbacks.append(fb)

    trainee_info[uuid] = {
        "styles": styles,
        "entertainments": entertainments,
        "feedback": feedbacks  # 리스트로 저장!
    }

def generate_prompt_for_trainee(trainee_uuid, cluster_id):
    # 자기 자신을 포함한 클러스터 멤버 추출
    cluster_members = df[(df["cluster"] == cluster_id) & (df["uuid"] != trainee_uuid)]
    cluster_size = len(cluster_members)

    # 클러스터에 다른 연습생이 없으면 None 반환
    if cluster_size < 1:
        return None, []

    # 샘플링: 자기 자신을 항상 포함
    sampled_uuids = [trainee_uuid]  # 자기 자신을 포함

    # 클러스터에 다른 연습생이 있을 경우 샘플링
    if cluster_size <= 4:
        sampled_uuids.extend(cluster_members["uuid"].tolist())  # 나머지 연습생들 추가
    else:
        # 샘플링 수를 클러스터 크기에 맞춰 결정
        sample_size = random.randint(3,5)
        sampled_uuids.extend(random.sample(cluster_members["uuid"].tolist(), sample_size))

    feedbacks, styles, entertainments = [], [], []
    for suid in sampled_uuids:
        data = trainee_info[suid]
        feedbacks.append(data["feedback"] if data["feedback"] else "피드백 없음")
        styles.append(", ".join(data["styles"]))
        entertainments.append(", ".join(data["entertainments"]))

    style_description = ", ".join(set(styles))
    recommendation_agency = ", ".join(set(entertainments))
    feedback_description = "다양한" if any(f != "피드백 없음" for f in feedbacks) else "피드백 없음"
    feedback_samples = "\n".join([f"연습생 {i+1}: {f}" for i, f in enumerate(feedbacks)])
    style_samples = "\n".join([f"연습생 {i+1}: {s}" for i, s in enumerate(styles)])
    entertainment_samples = "\n".join([f"연습생 {i+1}: {e}" for i, e in enumerate(entertainments)])

    prompt_template = f"""
    다음의 <order>에 따라 아래의 정보를 가진 연습생을 찾는 질문을 생성하세요.
    최종적으로 생성된 질문은 반드시 특정 연습생을 지칭하는 것이 아닌 후보 연습생을 찾는 질문이어야 합니다.
    
    <order>
    1. 아래의 연습생 정보를 확인하고 연예 기획사가 그 연습생을 필요로 할만한 구체적인 상황 시나리오를 작성합니다.
    2. 연습생 스타일과 피드백 정보에 표현된 단어를 대중적으로 사용되는 비슷한 의미의 단어로 바꾸어 시나리오를 작성합니다.
    3. 시나리오는 최신 트렌드를 반영하여 연예 기획사가 아래의 정보를 가진 연습생들을 찾기 위한 상황을 구체적으로 가정하여 작성합니다.
    4. 작성된 시나리오를 기반으로 에이전트가 해당 연습생 군집을 찾는 모집글을 5개 생성합니다.
    5. 질문은 연에 기획사가 실제로 사용할법한 대중적으로 사용되는 언어로 어색하지 않게 작성되어야합니다. 
    6. 한 질문당 30~100 토큰 사이의 질문으로 생성합니다. 
    7. 연습생의 단점을 이용하여 질문을 생성하지 않아야합니다.
    8. 반드시 생성된 질문만 반환합니다.

    [연습생 피드백 정보]: {feedback_samples}
    [연습생 스타일]: {style_samples}
    """

    prompt = prompt_template.format(
        style_description=style_description,
        recommendation_agency=recommendation_agency,
        feedback_description=feedback_description,
        feedback_samples=feedback_samples,
        style_samples=style_samples,
        entertainment_samples=entertainment_samples
    ).strip()

    return prompt, sampled_uuids

# 4. 연습생 기준 프롬프트 생성 + 저장
with open(OUTPUT_FILE, "w", encoding="utf-8") as fout:
    count = 0
    for idx, row in df.iterrows():
        uuid = row["uuid"]
        cluster_id = row["cluster"]
        prompt, sampled_uuids = generate_prompt_for_trainee(uuid, cluster_id)

        if prompt:
            messages = [
                {"role": "system", "content": "당신은 연예계 에이전트로 연습생과 연예 기획사를 연결시켜주는 역할을 하는 사람입니다."},
                {"role": "user", "content": prompt}
            ]
            fout.write(json.dumps({
                "custom_id": f"{uuid}_{'_'.join(sampled_uuids)}",
                "method": "POST",
                "url": "/v1/chat/completions",
                "body": {
                    "model": "gpt-4o-mini",
                    "messages": messages
                }
            }, ensure_ascii=False) + "\n")
            count += 1

print(f"{count}개의 GPT batch 요청이 생성되었습니다 → {OUTPUT_FILE}")