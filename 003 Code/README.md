# 국립한밭대학교 2025 캡스톤디자인 
## 팀 LLG / PDF 문서 파싱 기반 RAG 파이프라인

사용 방법 

**git clone 받기**

RAG Pipeline을 사용하기 위해 Repository를 clone 합니다.
```
git clone https://github.com/25capstoneRAG/rag_pipeline.git
```


**1. 데이터베이스 준비**

1-1. PDF문서 처리 이후 DB에 업로드하기 위해 DB를 준비합니다.

서버에 PostgreSQL을 설치합니다.
```
sudo apt update
sudo apt install postgresql postgresql-contrib
```

postgresql을 실행합니다.

```
sudo systemctl start postgresql

sudo -u postgres psql

CREATE USER <유저이름>
CREATE DATABASE <데이터베이스 이름>
\q

psql -h localhost -U <유저이름> -d <데이터베이스 이름>
```

1-2. 텍스트 / 이미지 데이터 저장을 위해 Table을 생성합니다.

```
-- 1. Tag (폴더)
CREATE TABLE Tag (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE,
    color VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Raw (원본 PDF 파일 바이너리)
CREATE TABLE Raw (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_data BYTEA NOT NULL
);

-- 3. Pdf (문서 메타데이터 및 연결 허브)
CREATE TABLE Pdf (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tag_id UUID REFERENCES Tag(id) ON DELETE SET NULL,
    raw_id UUID REFERENCES Raw(id) ON DELETE CASCADE,
    file_name VARCHAR(255) NOT NULL,
    file_size BIGINT,
    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_status VARCHAR(50) DEFAULT 'processing'
);

-- 4. Text (텍스트 청크, 순서 정보 포함)
CREATE TABLE Text (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pdf_id UUID REFERENCES Pdf(id) ON DELETE CASCADE,
    content TEXT,
    chunk_index INT NOT NULL,
    metadata JSONB
);

-- 5. Image (이미지)
CREATE TABLE Image (
    id VARCHAR(255) PRIMARY KEY,
    pdf_id UUID REFERENCES Pdf(id) ON DELETE CASCADE,
    image_data BYTEA NOT NULL,
    image_index INT
);
```

1-3. 만약 db의 포트가 열려있지 않은 경우 다음을 진행합니다.
```
1. /etc/postgresql/16/main/postgresql.conf의 listen_addresses 주석을 해제합니다.
2. 터미널을 새로 열어 3.의 코드를 입력합니다.
3. ssh -p <포트번호> -L 5432:localhost:5432 <유저이름>@<서버주소>
4. 이후 [2.PDF 파싱 및 DB 업로드]항목의 CRAGD 프로그램에 localhost, 5432포트로 접속합니다.
```
 

**2. PDF 파싱 및 DB 업로드**

2-1. 프로그램 실행에 앞서 PyMuPDF를 사용하기 위해 실행 환경에 맞게 패키지를 다운로드합니다.

```
pip3 install pymupdf==1.26.4 (Mac) / pip install pymupdf==1.26.4 (Windows)

```
현재 최신 버전인 1.26.5 버전에 오류가 있어 이전 버전인 1.26.4 버전으로 설치합니다. { Rect.get_area() 오류 }


2-2. 실행 환경에 맞게 CustomRAG Database 프로그램을 실행합니다. 프로그램은 github의 Release 항목에 있습니다.

```
CRAGD-1.0.0-arm64.dmg (Mac) / CRAGD Setup 1.0.0.exe(Windows)
```

Mac으로 실행 시 보안 정책 이슈로 다음의 명령어를 입력해야합니다.
```
xattr -cr /Applications/CRAGD.app
```

2-3. 이후 데이터베이스 항목으로 이동하여 "연결 설정" 부분에 위에서 설정한 데이터베이스의 정보를 입력하고 연결 버튼을 클릭합니다.

업로드 항목으로 이동하여 업로드하고자하는 PDF문서를 선택하거나 드래그 앤 드롭하여 DB에 저장합니다.

문서 항목으로 이동하여 DB에 저장되어있는 PDF문서를 관리합니다.


**3. DPR(단일 벡터 검색기) 학습(선택사항)**

DPR 학습은 다음의 레포지토리를 참고하여 진행 후 학습된 인코더를 rag_server/models에 같은 이름으로 덮어쓰기합니다.

```
https://github.com/25capstoneRAG/doc_retrieval
```

**4. VectorDB 구축**

DPR을 위해 CRAGD 프로그램을 통해 업로드한 문서를 Encoding 합니다.

이 항목부터는 RAG를 서비스하는 서버에서 진행합니다.

4-1. 서버에 접속 후 Repository를 clone 합니다.
```
git clone https://github.com/25capstoneRAG/rag_pipeline.git
```

4-2. 프로젝트 루트로 이동 후 다음의 디렉토리로 이동합니다.
```
cd ./rag_server/doc_retrieval/database
```

새 파일을 눌러 config.json 파일을 생성합니다. 내용은 다음과 같이 작성 후 저장합니다.
```
{
  "database": {
    "host": "localhost",
    "port": 5432,
    "dbname": "<데이터베이스 이름>",
    "user": "<유저이름>",
    "password": "<비밀번호>"
  }
}
```
4-3. bm25 인덱스와 chroma db는 [5-1. 챗봇 실행] 이후에 자동으로 실행합니다.


**5. 챗봇 실행**

5-1. Docker Compose를 사용해 챗봇의 프론트엔드, 백엔드, RAG 모듈을 모두 실행합니다.

```
docker-compose up --build 
```

5-2. [4-4. ChromaDB 구축]항목의 chroma db 구축 코드를 실행합니다.

서비스 준비가 완료되었습니다.

localhost:3000에 접속하여 서비스를 실행합니다.

5-3. 응답 가능한 문서를 CRAGD를 통해 업데이트한다면 4-3, 4-4 항목 실행 후 5-1 항목의 명령어를 실행합니다.
