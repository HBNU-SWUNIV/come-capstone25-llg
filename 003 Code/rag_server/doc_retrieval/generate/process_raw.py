import json
from collections import defaultdict

def parse_favorite_style(style_str):
    styles = style_str.split(",")
    result_map = {}

    for s in styles:
        s = s.strip()
        if "상" in s:
            result_map.setdefault("image", []).append(s)
        elif "MBTI" in s:
            result_map.setdefault("MBTI", []).append(s.replace("MBTI", "").strip())
        else:
            result_map.setdefault("Style", []).append(s)

    result = []
    for key, values in result_map.items():
        result.append({key: ",".join(values)})

    return result

def process_passage(input_path, output_path):
    try:
        with open(input_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
    except FileNotFoundError:
        print(f"❌ 파일을 찾을 수 없습니다: {input_path}")
        return
    except json.JSONDecodeError:
        print("❌ 유효한 JSON 형식이 아닙니다.")
        return

    if not isinstance(data, dict) or "content" not in data or "trainee" not in data:
        print("❌ 'content' 또는 'trainee' 키가 누락되었거나 형식이 올바르지 않습니다.")
        return

    content_data = data["content"]
    trainee_data = data["trainee"]

    # content를 uuid 기준으로 그룹화
    content_by_uuid = defaultdict(list)
    for c in content_data:
        uuid = c["uuid"]
        if "feedback" in c and "result" in c["feedback"] and c["feedback"]["result"]:
            content_by_uuid[uuid].append(c)

    # 최종 데이터 구성
    passage = []
    for trainee in trainee_data:
        uuid = trainee["uuid"]
        matched_contents = content_by_uuid.get(uuid, [])
        if not matched_contents:
            continue

        entry = {
            "uuid": uuid,
            "trainee": {
                "birth": trainee["birth"],
                "gender": trainee["gender"],
                "favoriteStyle": parse_favorite_style(trainee.get("favoriteStyle", ""))
            },
            "content": []
        }

        for c in matched_contents:
            content_entry = {}

            if c["type"] == "VIDEO" and "practiceType" in c:
                content_entry["practiceType"] = c["practiceType"]

            if c.get("style"):
                content_entry["style"] = [{"Style": c["style"].split(",")}]

            feedback_list = c["feedback"]["result"]
            if not feedback_list or not feedback_list[0]:
                continue

            feedback_descs = []
            recommend_entertains = []
            for fb in feedback_list[0]:
                desc = fb.get("feedbackDesc")
                if desc:
                    feedback_descs.append(desc.strip())

                entertain = fb.get("recommendEntertain")
                if entertain:
                    recommend_entertains.append(entertain)

            if not feedback_descs:
                continue

            content_entry["feedback"] = feedback_descs
            content_entry["recommendEntertain"] = recommend_entertains if recommend_entertains else []

            entry["content"].append(content_entry)

        if entry["content"]:
            passage.append(entry)

    # 저장
    result = {"passage": passage}
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"✅ 최종 데이터가 성공적으로 생성되었습니다: {output_path}")
    except Exception as e:
        print(f"❌ 파일 저장 중 오류 발생: {e}")

# 실행 예시
input_path = "log_data"
output_path = "passage_final.json"
process_passage(input_path, output_path)