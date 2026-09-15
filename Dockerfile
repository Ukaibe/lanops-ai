FROM python:3.14-slim AS builder
WORKDIR /app
RUN pip install --no-cache-dir uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

FROM python:3.14-slim
RUN apt-get update && apt-get install --no-install-recommends -y iputils-ping \
    && rm -rf /var/lib/apt/lists/*
RUN useradd --create-home --uid 10001 lanops
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY main.py ./
COPY lanops_ai ./lanops_ai
RUN mkdir -p /data && chown -R lanops:lanops /app /data
USER lanops
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
EXPOSE 8000 1514/udp
HEALTHCHECK --interval=30s --timeout=3s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
