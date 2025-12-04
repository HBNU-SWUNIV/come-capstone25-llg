from huggingface_hub import snapshot_download

model_id = "Qwen/Qwen2.5-7B-Instruct"
local_dir = "./model/Qwen2.5-7B-Instruct"

snapshot_download(
    repo_id=model_id,
    local_dir=local_dir,
    local_dir_use_symlinks=False
)
print("다운로드 완료!")