import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=BASE_DIR / ".env")


def load_api_key():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise Exception(
            "API 키 로드 실패: 환경변수 'OPENAI_API_KEY'가 설정되어 있지 않습니다."
        )
    return api_key
