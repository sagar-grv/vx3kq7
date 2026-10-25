# WindSight - single-image build: React frontend + FastAPI backend + bundled Jan 2026 dataset
FROM node:22-alpine AS frontend
WORKDIR /build/frontend
COPY frontend/package.json ./
RUN npm install --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 \
    PORT=8000 \
    FRONTEND_DIST=/app/frontend/dist \
    DB_PATH=/app/data/wind.db
WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend/ backend/
COPY --from=frontend /build/frontend/dist frontend/dist
COPY data/wind.db data/wind.db
COPY scripts/entrypoint.sh scripts/entrypoint.sh
RUN chmod +x scripts/entrypoint.sh
EXPOSE 8000
CMD ["scripts/entrypoint.sh"]
