FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y gcc g++ && rm -rf /var/lib/apt/lists/*

COPY backend/pyproject.toml backend/README.md ./
COPY backend/app ./app
COPY backend/enrichment ./enrichment
COPY backend/start.sh ./start.sh

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir transformers sentencepiece spacy && \
    python -m spacy download en_core_web_sm

# Store HF models inside /app so chown covers them and appuser can read at runtime
ENV HF_HOME=/app/hf_cache
ENV TRANSFORMERS_CACHE=/app/hf_cache

# Pre-bake models into image (TRANSFORMERS_OFFLINE not set yet — download allowed here)
RUN python -c "from transformers import pipeline; pipeline('sentiment-analysis', model='cardiffnlp/twitter-roberta-base-sentiment-latest', device=-1)" || true && \
    python -c "from transformers import pipeline; pipeline('zero-shot-classification', model='cross-encoder/nli-distilroberta-base', device=-1)" || true

# After pre-bake: skip HF API network checks at runtime (models are in /app/hf_cache)
ENV TRANSFORMERS_OFFLINE=1
ENV HF_DATASETS_OFFLINE=1

RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["bash", "start.sh"]
