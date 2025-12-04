import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

from config import load_api_key

MODEL_ID = os.getenv("MODEL_ID", "gpt-4o-mini")

client = OpenAI(api_key=load_api_key())


def generate_answer(prompt: str) -> str:
    try:
        response = client.responses.create(
            model=MODEL_ID,
            input=prompt,
            max_output_tokens=int(os.getenv("out_seq_length", 1024)),
            temperature=float(os.getenv("temperature", 0.7)),
            top_p=float(os.getenv("top_p", 0.9)),
        )
        return response.output_text.strip()
    except Exception as e:
        return f"Error during generation: {e}"


# ===================================================================
# ===================================================================
# ===================================================================
# ===================================================================
# import os
# import logging
# import torch
# from transformers import AutoTokenizer, AutoModelForCausalLM, GenerationConfig, BitsAndBytesConfig

# logger = logging.getLogger("rag")

# # [중요] 폴더명 대소문자/버전 정확히 확인 (Qwen2.5-7B-Instruct)
# model_path = "/app/model/qwen2.5-7b-instruct"

# # DEVICE 설정
# DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
# logger.info(f"[generate_answer] Using device: {DEVICE}")

# bnb_config = BitsAndBytesConfig(
#     load_in_4bit=True,
#     bnb_4bit_compute_dtype=torch.float16
# )

# try:
#     logger.info(f"[generate_answer] Loading local model: {model_path}")
#     tokenizer = AutoTokenizer.from_pretrained(model_path)

#     # [핵심 1] 단일 GPU 사용 시 cuda:0 강제 (속도 및 멀티 GPU 충돌 방지)
#     model = AutoModelForCausalLM.from_pretrained(
#         model_path,
#         quantization_config=bnb_config,
#         device_map="cuda:0"
#     )

#     model.eval()
#     logger.info("[generate_answer] Model and tokenizer loaded successfully.")
# except Exception as e:
#     logger.error(f"[generate_answer] Failed to load local model {model_path}: {e}")
#     tokenizer = None
#     model = None

# # 생성 설정
# GEN_CONFIG = GenerationConfig(
#     do_sample=os.getenv("greedy", "false").lower() != "true",
#     top_p=float(os.getenv("top_p", 0.9)),
#     top_k=int(os.getenv("top_k", 40)),
#     repetition_penalty=float(os.getenv("repetition_penalty", 1.1)),
#     temperature=float(os.getenv("temperature", 0.7)),
#     max_new_tokens=int(os.getenv("out_seq_length", 1024)), 
# )

# def generate_answer(prompt: str) -> str:
#     if model is None or tokenizer is None:
#         logger.error("[generate_answer] Model/tokenizer is not loaded.")
#         return "Error: Local LLM model is not loaded properly."

#     try:
#         # [핵심 2] Chat Template 적용 (Qwen Instruct 모델 필수)
#         # 단순히 prompt만 넣는 게 아니라, role을 지정해줘야 모델이 질문/답변을 이해함
#         messages = [
#             {"role": "system", "content": "문서 내용에 기반하여 사용자의 질문에 답변하세요.\n문서에 없는 내용은 추측하지 말고 모르겠다고 답변하세요.\n답변은 반드시 한국어로 하세요."},
#             {"role": "user", "content": prompt}
#         ]
#         logger.info(f"[generate_answer] Messages: {messages}")
#         # 템플릿을 적용하여 텍스트로 변환 (토크나이징은 아직 안 함)
#         text = tokenizer.apply_chat_template(
#             messages,
#             tokenize=False,
#             add_generation_prompt=True # 답변이 시작될 부분(<|im_start|>assistant)을 자동으로 붙여줌
#         )

#         # [핵심 3] 토크나이징 및 GPU 이동
#         model_inputs = tokenizer(
#             [text], 
#             return_tensors="pt"
#         ).to("cuda:0")

#         # 입력 토큰의 길이 측정 (답변만 잘라내기 위함)
#         input_len = model_inputs.input_ids.shape[1]

#         with torch.no_grad():
#             generated_ids = model.generate(
#                 **model_inputs,
#                 generation_config=GEN_CONFIG
#             )

#         # [핵심 4] 입력 길이만큼 앞부분을 잘라냄 (Slicing) - 가장 정확한 파싱 방법
#         # generated_ids[0]에는 [입력토큰 + 출력토큰]이 들어있으므로
#         # input_len 이후부터가 진짜 답변임
#         generated_ids = [
#             output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
#         ]

#         # 디코딩
#         response = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
        
#         logger.info(f"생성된 답변: {response[:100]}...") # 로그 확인

#         return response.strip()

#     except Exception as e:
#         logger.error(f"[generate_answer] Error during generation: {e}")
#         return f"Error during generation: {e}"