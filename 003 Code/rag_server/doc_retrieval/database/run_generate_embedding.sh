#!/bin/sh

# If you wanna use more gpus, set GPU_ID like "0, 1, 2"

GPU_ID=0
CUDA_VISIBLE_DEVICES=$GPU_ID python3 generate_embedding.py \
    	--model '../model/context_encoder' \
        --wiki_path '../data/corpus.jsonl' \
        --valid_data '../data/test.json' \
        --save_path '../data/faiss/' \
        --save_context \
        --train_bm25 \
        --pooler 'cls' \
        --num_sent 5 \
        --overlap 0 \
        --max_length 512 \
        --batch_size 128 \
        --cpu_workers 50
