FROM python:3.10-slim

WORKDIR /app

# Sistem bagimliliklari
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Python bagimliliklari
COPY pyproject.toml .
RUN pip install --no-cache-dir \
    numpy \
    scipy \
    pandas \
    scikit-learn \
    matplotlib \
    fastapi \
    uvicorn[standard] \
    jinja2 \
    python-multipart \
    reportlab

# Uygulama dosyalari
COPY src/ src/
COPY web/ web/
COPY batch_analyze.py .
COPY test_validation.py .

# Cikti dizinleri
RUN mkdir -p reports uploads

# Portlar
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

# Baslat
CMD ["uvicorn", "web.app:app", "--host", "0.0.0.0", "--port", "8000"]
