FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

# entrypoint.sh runs `alembic upgrade head` then starts uvicorn.
# PORT is injected by Render at runtime (defaults to 8000 locally).
CMD ["/app/entrypoint.sh"]
