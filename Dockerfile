FROM python:3.13-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src

COPY pyproject.toml README.md LICENSE ./
COPY src/ ./src/

RUN pip install --no-cache-dir .

EXPOSE 6379 9121

VOLUME ["/app/data"]

CMD ["nomdb-server", "--host", "0.0.0.0", "--port", "6379", "--data-dir", "/app/data"]
