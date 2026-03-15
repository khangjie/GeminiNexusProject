# ── Build stage ──────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ── Runtime stage ─────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application source
COPY backend/ ./backend/
COPY agents/ ./agents/

# Cloud Run injects PORT env variable; default to 8080
ENV PORT=8080

# Ensure backend package imports and top-level agents package are both visible.
ENV PYTHONPATH=/app:/app/backend

# Non-root user for security
RUN adduser --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser

EXPOSE 8080

# Use uvicorn with the number of workers appropriate for Cloud Run
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port $PORT --workers 1"]
