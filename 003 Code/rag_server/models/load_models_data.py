import os
import logging
from transformers import AutoTokenizer, AutoModel
from pathlib import Path

logger = logging.getLogger("rag")


def load_models_and_data(is_consultant_mode: bool):
    current_dir = Path(__file__).resolve().parent

    qe_local_path = current_dir / "question_encoder"

    model_path: str

    if qe_local_path.is_dir() and (qe_local_path / "config.json").is_file():
        model_path = str(qe_local_path)
        logger.info(f"Local trained question encoder found at: {model_path}")
    else:
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
