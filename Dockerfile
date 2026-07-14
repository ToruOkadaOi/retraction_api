FROM python:3.10-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    fastapi>=0.109.0 \
    "uvicorn[standard]>=0.27.0" \
    sqlalchemy>=2.0.0 \
    pydantic>=2.5.0 \
    "pydantic-settings>=2.0.0"

COPY . .

RUN mkdir -p data && \
    CSV_PATH=retraction_watch.csv \
    DATABASE_URL=sqlite:///./data/retraction_watch.db \
    python scripts/ingest_csv.py

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
