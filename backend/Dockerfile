# Minimal production image for the AuraDesk backend.
# Railway can also build this via Nixpacks auto-detection without a
# Dockerfile at all — this is provided for reproducibility and to match
# exactly what's tested locally, not because Railway requires it.

FROM python:3.12-slim AS base

# Dependency layer cached separately from app code — rebuilding after a
# code-only change doesn't reinstall dependencies.
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run as a non-root user — the base python:slim image runs as root by default.
RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app
USER appuser

# Railway injects PORT at runtime; default here only matters for local
# `docker run` testing without Railway's environment.
ENV PORT=8000
EXPOSE 8000

# No secrets are baked into this image — every credential comes from
# the runtime environment (Railway's environment variables), never
# COPY'd in or hardcoded.

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
