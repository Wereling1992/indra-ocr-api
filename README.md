# Indra OCR API

[![Docker](https://img.shields.io/badge/docker-ready-blue?logo=docker)](https://hub.docker.com/r/wereling1992/indra-ocr-api)
[![License](https://img.shields.io/badge/license-Apache%202.0-green)](LICENSE)

Lightweight **CPU-only OCR API** powered by the official [indra-ocr](https://github.com/datalab-to/indra) (Datalab) + FastAPI.

Turn images & PDFs into **Markdown**, plain text, or structured JSON (with line boxes + layout blocks).

## Quick Start

### Docker (recommended)

```bash
docker run -d -p 8000:8000 --name indra-ocr-api wereling1992/indra-ocr-api:latest

# Health check
curl http://localhost:8000/health

# OCR an image
curl -F "file=@receipt.jpg" -F "format=md" http://localhost:8000/ocr

# OCR a PDF
curl -F "file=@document.pdf" -F "format=json" -F "max_pages=10" http://localhost:8000/ocr
```

API docs → http://localhost:8000/docs

### Docker Compose

```bash
docker compose up --build -d
```

### Local (without Docker)

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn server:app --reload --port 8000
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check + model status |
| `POST` | `/ocr` | Upload image or PDF → OCR result |
| `POST` | `/ocr/image` | Image-only shortcut |

### `POST /ocr` parameters (multipart/form-data)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `file` | file | required | Image (png/jpg/webp/tiff…) or PDF |
| `format` | string | `md` | `md` / `text` / `json` |
| `mode` | string | `auto` | `auto` / `ocr` / `text` (PDF text-layer policy) |
| `max_pages` | int | `50` | Max pages for multi-page PDFs |

### Example response

```json
{
  "status": "success",
  "filename": "scan.png",
  "total_ms": 312.4,
  "pages": [
    {
      "page": 0,
      "source": "ocr",
      "markdown": "# Invoice\n\nTotal: $42.00",
      "text": "Invoice\nTotal: $42.00",
      "rotation": 0.0,
      "skew": 0.3,
      "lines": [],
      "blocks": [],
      "timings": {"total_ms": 298.1}
    }
  ]
}
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `INDRA_THREADS` | `4` | ONNX Runtime intra-op threads |
| `MAX_UPLOAD_MB` | `20` | Max upload size (MB) |
| `MAX_PAGES` | `50` | Default max pages |
| `PORT` | `8000` | Listen port |

## Resource Recommendation

| Scenario | RAM | CPU |
|----------|-----|-----|
| Minimum | 1.5–2 GB | 2 cores |
| Comfortable | 2–4 GB | 2–4 cores |

- Uses **single Uvicorn worker** (recommended with ONNX Runtime)
- Models (~76 MB) are **pre-baked** into the image → fast cold start

## Build & Publish

```bash
# Build
docker build -t wereling1992/indra-ocr-api:1.0.0 .
docker tag wereling1992/indra-ocr-api:1.0.0 wereling1992/indra-ocr-api:latest

# Push to Docker Hub
docker login
docker push wereling1992/indra-ocr-api:1.0.0
docker push wereling1992/indra-ocr-api:latest
```

Platform: `linux/amd64` by default.

## License

- **This repository (code)**: [Apache-2.0](LICENSE)
- **Model weights** (`indra-ocr`): Modified [OpenRAIL-M](https://huggingface.co/datalab-to/indra-ocr)  
  Free for research, personal use, and organizations under $20M funding/revenue.  
  Commercial use beyond the license terms requires a paid license from Datalab.

## Credits

- [datalab-to/indra](https://github.com/datalab-to/indra) – official Indra OCR
- FastAPI + Uvicorn
