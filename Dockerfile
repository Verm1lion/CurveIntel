FROM python:3.10-slim

WORKDIR /app

# System dependencies required by native Python wheels.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy the application before installing so Docker uses the project metadata.
COPY pyproject.toml README.md ./
COPY alembic.ini ./
COPY alembic/ alembic/
COPY src/ src/
COPY web/ web/
COPY batch_analyze.py ./
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

# Install runtime dependencies from pyproject.toml.
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

# Runtime directories and entrypoint.
RUN chmod +x /usr/local/bin/docker-entrypoint.sh \
    && mkdir -p reports uploads

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["uvicorn", "web.app:app", "--host", "0.0.0.0", "--port", "8000"]
