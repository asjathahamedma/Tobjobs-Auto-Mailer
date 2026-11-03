FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app
COPY web_backend/requirements.txt /app/web_backend/requirements.txt
RUN pip install --no-cache-dir -r /app/web_backend/requirements.txt

COPY src /app/src
COPY web_backend /app/web_backend

EXPOSE 8000
CMD ["sh", "-c", "uvicorn web_backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
