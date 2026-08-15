# ── Stage 1: build frontend ──
FROM node:20-slim AS frontend
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
# Override outDir so build stays inside container
RUN npm run build -- --outDir dist

# ── Stage 2: backend + built assets ──
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
# Copy frontend build into static/
COPY --from=frontend /app/dist ./static
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]