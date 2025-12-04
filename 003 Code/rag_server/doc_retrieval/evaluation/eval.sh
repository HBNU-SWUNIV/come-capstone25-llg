# python eval.py \
#   --data_path valid.json \
#   --full_document_data_path chunked_corpus.json \
#   --model_type cross \
#   --model_path path/to/cross_model \

# dpr
python eval.py \
  --data_path /home/kilab_kdh/DPR-KO/code/valid.json \
  --full_document_data_path /home/kilab_kdh/DPR-KO/code/chunked_corpus.jsonl \
  --model_type dpr \
  --model_path /home/kilab_kdh/DPR-KO/pretrained_model/question_encoder/klue_epoch9_top1_0.0862\
  --passage_encoder_path /home/kilab_kdh/DPR-KO/pretrained_model/context_encoder/klue_epoch9_top1_0.0862 \
  --use_faiss \
  --faiss_index_path /home/kilab_kdh/DPR-KO/pickles/faiss_pickle.pkl \

# cross
# GPU_ID=0
# CUDA_VISIBLE_DEVICES=$GPU_ID python3 cross_eval.py \
#   --data_path /home/kilab_kdh/doc_retrieval/DPR-KO/code/ex7/test_ex7.json \
#   --full_document_data_path /home/kilab_kdh/doc_retrieval/DPR-KO/code/ex7/corpus_1_1.jsonl \
#   --model_path /home/kilab_kdh/doc_retrieval/DPR-KO/pretrained_model/cross/ms-marco-MiniLM-L6-v2_margin_ex7_output/epoch_5 \
#   --top_k 1,5,10,20,50,100