# to build image
# docker build -t sportsdash .
# ── Stage 1: build the React app ───────────────────────────────────────────
FROM node:22-alpine AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ── Stage 2: Python API that also serves the built app ─────────────────────
FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    SPORTSDASH_CONFIG=/app/config.yaml \
    SPORTSDASH_STATIC=/app/static

WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/sportsdash ./sportsdash
COPY config.yaml ./config.yaml
COPY --from=web /web/dist ./static

RUN useradd --system --uid 1000 app
USER app

EXPOSE 8000
HEALTHCHECK --interval=60s --timeout=5s --start-period=15s \
  CMD python -c "import urllib.request,os; urllib.request.urlopen(f'http://127.0.0.1:{os.environ[\"PORT\"]}/api/health', timeout=4)"

# One process keeps one in-memory cache; FastAPI runs the sync routes on a thread pool.
CMD ["sh", "-c", "uvicorn sportsdash.api:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
