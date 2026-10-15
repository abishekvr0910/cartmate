FROM node:22-bookworm-slim AS frontend-build
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CARTMATE_FRONTEND_DIST=/app/frontend/dist
WORKDIR /app
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend/ ./backend/
COPY ops/cartmate_backup.py ops/cartmate_restore.py ops/pilot_invites.py ops/pilot_preflight.py ./ops/
COPY --from=frontend-build /build/frontend/dist ./frontend/dist
WORKDIR /app/backend
CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port \"${PORT:-10000}\" --workers 1 --ws-max-size 65536 --log-level warning --no-access-log"]
