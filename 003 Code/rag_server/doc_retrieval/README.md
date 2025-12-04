## 단일 벡터 검색기 (DPR)

### 레퍼런스

**DPR:** [DPR](https://github.com/facebookresearch/DPR) /
**DPR-KO:** [DPR-KO](https://github.com/millet04/DPR-KO?tab=readme-ov-file)
(다음의 Repository를 참고하여 작성되었습니다.)
** **

**git clone 받기**

단일 벡터 검색기(DPR)을 사용하기 위해 Repository를 clone 합니다.
```
git clone https://github.com/25capstoneRAG/doc_retrieval.git
```

데이터 생성에 사용할 GPT API를 설정합니다.

apikey.env 파일 생성 후 다음 형식에 맞게 api 키를 환경변수로 등록합니다.
```
OPENAI_API_KEY=##apikey##
```

**데이터 준비**

검색기를 학습하기 위해 질문-응답의 데이터를 생성합니다.

**1. 데이터 전처리 - process_raw.py**

질의 생성을 위해 데이터 전처리를 수행합니다. 코드의 해당 부분에 실제 (로그)데이터 경로를 추가합니다.
```
input_path = "log_data" 

-----

python process_raw.py
```

**2. 클러스터 생성 - cluster_data.py**

질의를 생성하기 위해 비슷한 연습생 그룹을 형성합니다.
```
python cluster_data.py
```
**3. 질문 생성 - query_prompt.py**

연습생 정보를 이용하여 연습생 군집을 찾는 질의를 생성하는 프롬프트를 jsonl형식으로 저장합니다.
```
python query_prompt.py
```
**4. 배치 보내기 - submit_batch.py**
GPT Batch API를 사용하여 응답을 생성합니다.

```
python submit_batch.py
```
**5. 저장 - receive_query.py**

Batch가 완료되면 응답 정보를 받습니다. 코드의 해당 부분을 제출한 batch의 id로 변경합니다.

```
batch_id = "batch_id"

--------

python receive_query.py
```
**6. corpus 저장 - save_corpus.py**

지정된 corpus 형식으로 저장합니다.
```
python save_corpus.py
```
**7. query 저장 - save_query.py**

지정된 query 형식으로 저장합니다.

```
python save_query.py
```

**위의 코드로 생성된 최종 데이터의 형식은 다음과 같습니다.**

```
corpus.jsonl
{"_id": "", "title": "", "text": ""}

queries.jsonl
{"_id": "", "text": "", "metadata": {"source": ""}}

```
** **

**학습, 검증 데이터 준비**

학습, 검증을 위해 데이터를 QA 형식에 맞게 전처리합니다.

```
cd code
python process_train.py
{
  "question": "",
    "answers": "1",
    "positive": [
      {
        "title": "",
        "text": "",
        "idx": "2"
      },
      {
        "title": "",
        "text": "",
        "idx": "3"
      }
    ],
    "answer_idx": [
      "1",
      "2",
      "3"
    ]
  },

```

데이터를 같은 질문을 기준으로 묶습니다.
```
python process_valid.py
```


학습을 위해 train/valid/test 셋으로 분리합니다.
```
python train_valid.py
```

BM25를 이용해 train셋에 negative sampling을 진행합니다.
```
python negative_sampling.py
cd ..
```

**학습**

Encoder를 학습합니다.
```
cd train
sh run_train.sh
cd ../database
```

**인덱싱**


학습한 Encoder를 이용하여 문서를 인덱싱합니다.
```
faiss 인덱싱 - 실험/성능 테스트
sh run_generate_embedding.sh
cd ../evaluation

chroma 인덱싱 - rag pipeline용
python generate_chroma_index.py
```

chroma의 경우, 인덱싱할 corpus.jsonl의 경로를 rag_server/data에 작성해줘야 합니다.

**성능 측정**

학습한 Encoder와 인덱싱 정보를 이용해서 성능을 측정합니다.
```
run_evaluate_retrieval.sh
```





