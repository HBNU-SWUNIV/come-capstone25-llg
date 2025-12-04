#!/bin/sh

# If you wanna use more gpus, set GPU_ID like "0, 1, 2"

GPU_ID=0
CUDA_VISIBLE_DEVICES=$GPU_ID python3 train.py \
    	--model 'klue/bert-base' \
        --q_encoder_path 'snumin44/biencoder-ko-bert-question'\
        --c_encoder_path 'snumin44/biencoder-ko-bert-context'\
    	--train_data '../data/train.json' \
        --valid_data '../data/dev.json' \
        --q_output_path '../model/question_encoder' \
        --c_output_path '../model/context_encoder' \
    	--epochs 5 \
        --batch_size 32 \
        --max_length 512 \
        --dropout 0.1 \
        --learning_rate 1e-5 \
        --pooler 'cls' \
        --amp
