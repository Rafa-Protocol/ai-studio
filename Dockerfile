# --- STAGE 1: Build Frontend (Node.js) ---
FROM node:18 as frontend-builder

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install --legacy-peer-deps
COPY frontend/ .
RUN npm run build

# --- STAGE 2: Build Backend & Serve (Python) ---
FROM python:3.11-slim

WORKDIR /app/backend

# Install system dependencies
RUN apt-get update && apt-get install -y gcc libpq-dev build-essential && rm -rf /var/lib/apt/lists/*

# Copy backend requirements & install
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ .

# --- MERGE STEP ---
# Copy the BUILT frontend files from Stage 1 into the folder Python expects
# This places them at /app/frontend/build (relative to /app/backend)
COPY --from=frontend-builder /app/frontend/build ../frontend/build

# Start the server (Railway injects the PORT variable)
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}