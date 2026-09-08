# syntax=docker/dockerfile:1
# ---------------------------------------------------------------------------
# Stage 1 — build the React (TypeScript + Vite + Tailwind) frontend.
# Node is only ever present in this build stage; the final runtime image is
# Python-only, which keeps the running container's RAM footprint small
# enough for a 16GB student laptop.
# ---------------------------------------------------------------------------
FROM node:20-slim AS frontend-build
WORKDIR /frontend
COPY frontend/package.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# ---------------------------------------------------------------------------
# Stage 2 — Python runtime (FastAPI + local AI models).
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS runtime
WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./backend/requirements.txt

# CPU-only torch wheel by default (smaller download, works everywhere).
# scripts/setup.sh passes --build-arg TORCH_INDEX=<cuda wheel url> instead
# when it detects an NVIDIA GPU on the build host.
ARG TORCH_INDEX=https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir torch --index-url ${TORCH_INDEX} \
    && pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ ./backend/
COPY --from=frontend-build /frontend/dist ./frontend_dist

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/backend \
    HF_HOME=/app/hf_cache \
    TRANSFORMERS_CACHE=/app/hf_cache \
    DATA_DIR=/app/data \
    DATABASE_URL=sqlite:////app/data/app.db \
    CHROMA_PERSIST_DIR=/app/data/chroma \
    FRONTEND_DIST=/app/frontend_dist \
    PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=60s --retries=20 \
    CMD curl -fsS "http://localhost:${PORT}/api/health" || exit 1

WORKDIR /app/backend
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
