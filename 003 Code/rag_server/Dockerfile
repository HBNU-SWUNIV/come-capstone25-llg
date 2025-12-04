FROM python:3.10

RUN apt-get update && apt-get install -y \
    default-jdk \
    maven \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*
    
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .

RUN pip install --upgrade pip setuptools wheel \
    && pip install pyserini \
    && pip install -r requirements.txt

COPY . .

RUN chmod +x /app/entrypoint.sh

RUN find . -name "*.pyc" -delete && find . -name "__pycache__" -type d -exec rm -r {} +

EXPOSE 8001

ENTRYPOINT ["bash", "/app/entrypoint.sh"]
