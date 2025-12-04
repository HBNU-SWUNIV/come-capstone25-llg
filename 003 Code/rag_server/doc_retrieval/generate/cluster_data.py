import json
import pandas as pd
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.cluster import KMeans
from collections import defaultdict, Counter

# 파일 경로
INPUT_JSON = "doc_retrieval/generate/passage_final.json"
OUTPUT_CSV = "doc_retrieval/generate/clusters.csv"

# 1. JSON 데이터 불러오기
with open(INPUT_JSON, "r", encoding="utf-8") as f:
    data = json.load(f)

# 2. 필요한 필드 추출
records = []
for entry in data["passage"]:
    uuid = entry["uuid"]
    trainee = entry["trainee"]
    
    # 스타일 정보 (Look, image, MBTI, Style)
    styles = set()
    for d in trainee.get("favoriteStyle", []):
        for k, v in d.items():
            if isinstance(v, list):
                for item in v:
                    styles.add(f"{k}:{item}")
            else:
                styles.add(f"{k}:{v}")
    
    # 추천 엔터테인먼트
    entertainments = set()
    for c in entry.get("content", []):
        entertainments.update(c.get("recommendEntertain", []))

    records.append({
        "uuid": uuid,
        "styles": styles,
        "entertainments": entertainments
    })

df = pd.DataFrame(records)

# 3. 스타일 및 추천 엔터 벡터화 (One-hot encoding)
mlb_style = MultiLabelBinarizer()
style_encoded = mlb_style.fit_transform(df["styles"])

mlb_entertain = MultiLabelBinarizer()
ent_encoded = mlb_entertain.fit_transform(df["entertainments"])

# 4. feature 벡터 병합
import numpy as np
features = np.hstack([style_encoded, ent_encoded])

# 5. 클러스터 수 설정 (5~10명당 1클러스터 → 대략 500~1000개)
n_clusters = max(1, len(df) // 7)
kmeans = KMeans(n_clusters=n_clusters, random_state=42)
labels = kmeans.fit_predict(features)

# 6. 결과 저장
df["cluster"] = labels
df.to_csv(OUTPUT_CSV, index=False)
print(f"✅ 클러스터링 결과 저장 완료: {OUTPUT_CSV}")

# 7. 각 클러스터별 인원 수 확인 (선택적)
cluster_counts = Counter(labels)
print("\n[클러스터별 연습생 수 예시]")
for cluster_id, count in cluster_counts.most_common(10):
    print(f"Cluster {cluster_id}: {count}명")