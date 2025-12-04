import openai
import os
import json
from dotenv import load_dotenv
from openai import OpenAI
from pathlib import Path

# API 키 설정
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(dotenv_path=BASE_DIR / ".env")
openai.api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI()

# 경로 설정
OUTPUT_DIRECTORY = "doc_retrieval/generate"
batch_id = "batch_id"  # 실제 배치 ID로 변경 필요

batch = client.batches.retrieve(batch_id)

if batch.status == "completed":
    output_file_id = batch.output_file_id
    output_file = client.files.content(output_file_id)
    output_file_data = output_file.read().decode("utf-8")

    results = []

    for line in output_file_data.splitlines():
        try:
            data = json.loads(line)
            custom_id = data.get("custom_id", "")
            content = (
                data.get("response", {})
                .get("body", {})
                .get("choices", [{}])[0]
                .get("message", {})
                .get("content")
            )

            if "_" in custom_id:
                parts = custom_id.split("_")
                uuid = parts[0]
                roles = parts[1:]
                results.append({"uuid": uuid, "roles": roles, "response": content})

        except Exception as e:
            print(f"⚠️ JSON 파싱 오류: {e}")

    # 리스트 형태로 JSON 저장
    filtered_path = os.path.join(OUTPUT_DIRECTORY, "query_output.json")
    with open(filtered_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"✅ 필터링된 결과 저장 완료: {filtered_path}")
else:
    print(f"❌ 배치 작업이 완료되지 않았습니다. 상태: {batch.status}")
