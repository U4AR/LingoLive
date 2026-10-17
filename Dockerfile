FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8080
WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt && useradd --create-home appuser
COPY --chown=appuser:appuser backend /app/backend
COPY --chown=appuser:appuser shared /app/shared
COPY --chown=appuser:appuser web /app/web
USER appuser
CMD ["sh", "-c", "exec uvicorn backend.app:app --host 0.0.0.0 --port ${PORT:-8080} --no-access-log --ws-max-size 16000"]
