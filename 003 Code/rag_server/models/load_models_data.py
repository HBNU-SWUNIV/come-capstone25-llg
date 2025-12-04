import os
import logging
from transformers import AutoTokenizer, AutoModel
from pathlib import Path

logger = logging.getLogger("rag")


def load_models_and_data(is_consultant_mode: bool):
    # /home/.../rag_pipeline/rag_server/models
    current_dir = Path(__file__).resolve().parent

    # 같은 디렉토리 안의 question_encoder 폴더
    qe_local_path = current_dir / "question_encoder"

    # 기본값 None
    model_path: str

    # 1) 로컬 question_encoder 우선 사용
    if qe_local_path.is_dir() and (qe_local_path / "config.json").is_file():
        model_path = str(qe_local_path)
        logger.info(f"Local trained question encoder found at: {model_path}")
    else:
        # 2) 없으면 HF 모델로 fallback
        model_path = "snumin44/biencoder-ko-bert-question"
        logger.info(
            f"No local trained question encoder found in {qe_local_path}. "
            f"Falling back to: {model_path}"
        )

    try:
        logger.info(f"Loading model from: {model_path}")
        tokenizer = AutoTokenizer.from_pretrained(model_path)
        q_encoder = AutoModel.from_pretrained(model_path)

        logger.info("Model and tokenizer loaded successfully.")
        return tokenizer, q_encoder

    except Exception as e:
        logger.error(f"Failed to load model from {model_path}: {e}")

        # 모델 경로가 이미 HF fallback인 상태면 더 시도하지 않고 에러 그대로 올림
        if model_path != "snumin44/biencoder-ko-bert-question":
            logger.info("Attempting fallback to klue/roberta-base...")
            try:
                fallback_path = "klue/roberta-base"
                tokenizer = AutoTokenizer.from_pretrained(fallback_path)
                q_encoder = AutoModel.from_pretrained(fallback_path)
                logger.info("Fallback model klue/roberta-base loaded successfully.")
                return tokenizer, q_encoder
            except Exception as e2:
                logger.error(f"Fallback also failed: {e2}")
                raise e2
        else:
            raise e
