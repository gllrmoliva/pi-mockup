FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY pyproject.toml .
COPY app ./app
COPY alembic.ini .
COPY alembic ./alembic
COPY entrypoint.sh .
COPY logging.json .

RUN mkdir -p /app/uploads \
    && chmod +x entrypoint.sh \
    && adduser --disabled-password --gecos "" appuser \
    && chown -R appuser:appuser /app

USER appuser
EXPOSE 8000
ENTRYPOINT ["./entrypoint.sh"]

FROM base AS development

USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends libatomic1 \
    && rm -rf /var/lib/apt/lists/*
COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt
COPY tests ./tests
RUN chown -R appuser:appuser /app
USER appuser

FROM base AS production
