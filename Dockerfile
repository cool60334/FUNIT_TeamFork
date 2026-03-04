# ============================================================
# Stage 1: builder — install Python dependencies
# ============================================================
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build tools needed for some packages (e.g. sentence-transformers)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ============================================================
# Stage 2: runtime — minimal image, non-root user
# ============================================================
FROM python:3.11-slim AS runtime

WORKDIR /app

# NON_ROOT_SECURITY: create non-root user
RUN groupadd -r appuser && useradd -r -g appuser -m appuser

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy source code
COPY --chown=appuser:appuser agents/    ./agents/
COPY --chown=appuser:appuser utils/     ./utils/
COPY --chown=appuser:appuser scripts/   ./scripts/
COPY --chown=appuser:appuser config/    ./config/
COPY --chown=appuser:appuser hooks/     ./hooks/

# Runtime directories (volumes will be mounted here, ensure ownership)
RUN mkdir -p data outputs && chown appuser:appuser data outputs

# Switch to non-root user
USER appuser

# Default entrypoint — pass --topic etc. as CMD args
ENTRYPOINT ["python", "scripts/run_integration.py"]
