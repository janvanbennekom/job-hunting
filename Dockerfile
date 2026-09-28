# JobHunter application image (Streamlit + worker CLI)
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 appuser

COPY pyproject.toml README.md ./
COPY src ./src
COPY scripts ./scripts
COPY alembic ./alembic
COPY alembic.ini ./
COPY config/automation.example.json ./config/automation.example.json
COPY .streamlit ./.streamlit

RUN pip install --upgrade pip \
    && pip install -e . \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8501/_stcore/health || exit 1

# Default: Streamlit dashboard (override for worker / migrations)
CMD ["streamlit", "run", "src/jobhunter/ui/streamlit/app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
