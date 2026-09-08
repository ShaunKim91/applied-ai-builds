# Multi-stage build: Node builds the React SPA, the runtime image is
# Python-only (no Node left in the final image).
FROM node:20-slim AS frontend-build
WORKDIR /frontend
COPY frontend/package.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim AS runtime
ARG TORCH_INDEX=https://download.pytorch.org/whl/cpu
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir --index-url ${TORCH_INDEX} torch==2.8.0 \
    && pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ ./backend/
COPY --from=frontend-build /frontend/dist ./backend/frontend_dist

ENV HF_HOME=/app/hf_cache
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

WORKDIR /app/backend
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
