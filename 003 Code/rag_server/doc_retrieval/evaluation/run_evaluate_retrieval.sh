#!/bin/sh

# If you wanna use more gpus, set GPU_ID like "0, 1, 2"

GPU_ID=0
CUDA_VISIBLE_DEVICES=$GPU_ID python3 evaluate_retrieval.py \
    	--model '../model/question_encoder' \
        --valid_data '../data/test.json' \
        --faiss_path '../data/faiss/faiss_pickle.pkl' \
        --faiss_weight 1 \
        --search_k 2000 \
        --pooler 'cls'



