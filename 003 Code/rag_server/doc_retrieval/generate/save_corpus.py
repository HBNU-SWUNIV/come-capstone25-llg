import json

def flatten_favorite_style(favorite_style):
    desc = []
    for entry in favorite_style:
        for k, v in entry.items():
            desc.append(f"{v} {k.lower()}" if k != "MBTI" else f"{v} 성향의 MBTI")
    return ", ".join(desc)

def flatten_style(style):
    parts = []
    for entry in style:
        for k, v in entry.items():
            if isinstance(v, list):
                v = ", ".join(v)
            parts.append(f"{v} {k.lower()}")
    return ", ".join(parts)

def build_corpus_entries(passage_data):
    corpus = []
    for p in passage_data:
        uuid = p["uuid"]
        trainee = p["trainee"]
        birth = trainee.get("birth", "")
        gender = "남성" if trainee.get("gender") == "MAN" else "여성"
        fav_style = flatten_favorite_style(trainee.get("favoriteStyle", []))

        # 모든 content를 하나로 합치기
        content_texts = []
        for content in p["content"]:
            practice_type = content.get("practiceType", "Unknown")
            styles = flatten_style(content.get("style", []))
            feedbacks = content.get("feedback", [])
            feedback_text = "\n\n".join(feedbacks) if isinstance(feedbacks, list) else feedbacks

            text_parts = [
                f"[{practice_type}] 연습에서는 {styles} 스타일을 선보였고,",
                f"피드백: {feedback_text}" if feedback_text else "피드백 없음"
            ]
            content_texts.append("\n".join(text_parts))

        full_text = f"이 연습생은 {birth}의 {gender}으로, {fav_style} 스타일을 선호합니다.\n\n" + "\n\n".join(content_texts)

        corpus.append({
            "_id": uuid,
            "title": "연습생 연습 기록",
            "text": full_text
        })

    return corpus

# JSON 파일 읽기
with open("passage_final.json", "r", encoding="utf-8") as f:
    data = json.load(f)

corpus_entries = build_corpus_entries(data["passage"])

# JSONL로 저장
with open("../data/corpus.jsonl", "w", encoding="utf-8") as f:
    for entry in corpus_entries:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")