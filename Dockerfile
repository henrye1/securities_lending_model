# Securities Lending (Share Cover) Model - single-image deploy (Render).
# Stage 1: build the React SPA. Stage 2: FastAPI serves API + built UI.

FROM node:24-alpine AS frontend
WORKDIR /ui
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app/backend
COPY backend/pyproject.toml ./
COPY backend/app ./app
RUN pip install .
COPY --from=frontend /ui/dist /app/frontend/dist
ENV FRONTEND_DIST=/app/frontend/dist PORT=8003
EXPOSE 8003
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
