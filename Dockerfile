FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y gcc g++ && rm -rf /var/lib/apt/lists/*

COPY backend/pyproject.toml backend/README.md ./
COPY backend/app ./app
COPY backend/enrichment ./enrichment
COPY backend/indicators ./indicators
COPY backend/start.sh ./start.sh

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir transformers sentencepiece protobuf spacy && \
    python -m spacy download en_core_web_sm && \
    python -m spacy download xx_ent_wiki_sm

# Store HF models inside /app so chown covers them and appuser can read at runtime
ENV HF_HOME=/app/hf_cache
ENV TRANSFORMERS_CACHE=/app/hf_cache

# Pre-bake models into image (TRANSFORMERS_OFFLINE not set yet — download allowed here).
# English-only models (legacy NLP_MULTILINGUAL_MODE=off default):
RUN python -c "from transformers import pipeline; pipeline('sentiment-analysis', model='cardiffnlp/twitter-roberta-base-sentiment-latest', device=-1)" || true && \
    python -c "from transformers import pipeline; pipeline('zero-shot-classification', model='cross-encoder/nli-distilroberta-base', device=-1)" || true

# Multilingual models for NLP_MULTILINGUAL_MODE=shadow|on (issue #162).
# Only one model is loaded per phase. Framing uses multilingual MiniLM instead
# of mDeBERTa so the worker can complete cycles on Fly shared CPU/2GB.
RUN python -c "from transformers import pipeline; pipeline('sentiment-analysis', model='cardiffnlp/twitter-xlm-roberta-base-sentiment', device=-1)" || true && \
    python -c "from transformers import pipeline; pipeline('zero-shot-classification', model='MoritzLaurer/multilingual-MiniLMv2-L6-mnli-xnli', device=-1)" || true

# After pre-bake: skip HF API network checks at runtime (models are in /app/hf_cache)
ENV TRANSFORMERS_OFFLINE=1
ENV HF_DATASETS_OFFLINE=1
ENV NLP_MULTILINGUAL_MODE=off

RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["bash", "start.sh"]
