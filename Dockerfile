# Indra OCR API - Official Python indra-ocr + FastAPI
#
# Docker Hub: https://hub.docker.com/r/wereling1992/indra-ocr-api
#
# Build:
#   docker build -t wereling1992/indra-ocr-api:1.0.0 .
#   docker tag  wereling1992/indra-ocr-api:1.0.0 wereling1992/indra-ocr-api:latest
#
# Run:
#   docker run -d -p 8000:8000 wereling1992/indra-ocr-api:latest
#
# Push:
#   docker push wereling1992/indra-ocr-api:1.0.0
#   docker push wereling1992/indra-ocr-api:latest

FROM python:3.12-slim

# System deps for onnxruntime / opencv-headless
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download models during build so container starts instantly
# (models go to /root/.cache/huggingface by default)
RUN python -c "import indra_ocr; indra_ocr.load(threads=1); print('Models cached successfully')"

# App code
COPY server.py .

# Non-root user
RUN useradd -m -u 1000 appuser \
    && mkdir -p /home/appuser/.cache \
    && cp -r /root/.cache/huggingface /home/appuser/.cache/ 2>/dev/null || true \
    && chown -R appuser:appuser /home/appuser /app
USER appuser

ENV HOME=/home/appuser
ENV HF_HOME=/home/appuser/.cache/huggingface
ENV INDRA_THREADS=4
ENV MAX_UPLOAD_MB=20
ENV MAX_PAGES=50
ENV PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')" || exit 1

# Single worker is recommended (ONNX Runtime + shared model)
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
