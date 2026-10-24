FROM python:3.10-slim

WORKDIR /app

COPY requirements.lock ./
RUN pip install --no-cache-dir --require-hashes -r requirements.lock

COPY app ./app
COPY scripts ./scripts
COPY retraction_watch.csv ./

RUN mkdir -p data && \
    CSV_PATH=retraction_watch.csv \
    DATABASE_URL=sqlite:///./data/retraction_watch.db \
    python scripts/ingest_csv.py

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
