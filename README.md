# Indra OCR API

Lightweight **CPU-only** OCR API powered by the official [indra-ocr](https://github.com/datalab-to/indra) (Datalab) + FastAPI.

Turn images & PDFs into **Markdown**, plain text, or structured JSON (with line boxes + layout blocks).

**Docker Hub:** [wereling1992/indra-ocr-api](https://hub.docker.com/r/wereling1992/indra-ocr-api)

## Features

- Official Python indra-ocr (not a reimplementation)
- Supports images (PNG, JPG, WebP, TIFF…) and PDFs
- Output formats: Markdown / plain text / full JSON
- Models (~76 MB) pre-baked into the image → fast cold start
- Single Uvicorn worker (recommended for ONNX Runtime)
- Healthcheck included
- **CPU-only** — no GPU required

## Quick Start

### Docker (recommended)

```bash
docker run -d -p 8000:8000 --name indra-ocr-api wereling1992/indra-ocr-api:latest

# Health check
curl http://localhost:8000/health

# OCR an image
curl -F "file=@image.png" -F "format=md" http://localhost:8000/ocr

# OCR a PDF
curl -F "file=@document.pdf" -F "format=json" http://localhost:8000/ocr
```

API docs: http://localhost:8000/docs

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

## Environment Variables

| Variable      | Default | Description                  |
|---------------|---------|------------------------------|
| INDRA_THREADS | 4       | ONNX Runtime threads         |
| MAX_UPLOAD_MB | 20      | Max upload size (MB)         |
| MAX_PAGES     | 50      | Max pages for multi-page PDF |
| PORT          | 8000    | Listen port                  |

## Endpoints

| Method | Path       | Description          |
|--------|------------|----------------------|
| GET    | /health    | Health check         |
| POST   | /ocr       | Upload image or PDF  |
| POST   | /ocr/image | Image-only shortcut  |

### `POST /ocr` parameters (multipart/form-data)

| Field     | Type   | Default | Description                          |
|-----------|--------|---------|--------------------------------------|
| file      | file   | required| Image (png/jpg/webp/tiff…) or PDF    |
| format    | string | md      | md / text / json                     |
| mode      | string | auto    | auto / ocr / text (PDF text-layer)   |
| max_pages | int    | 50      | Max pages for multi-page PDFs        |

## Resource Recommendation

| Scenario  | RAM       | CPU      |
|-----------|-----------|----------|
| Minimum   | 1.5–2 GB  | 2 cores  |
| Recommend | 2–4 GB    | 2–4 cores|

## License

- **Code**: [Apache-2.0](LICENSE)
- **Model weights**: Modified [OpenRAIL-M](https://huggingface.co/datalab-to/indra-ocr)

> Free for research, personal use, and organizations under $20M funding/revenue. Commercial use beyond the license terms requires a paid license from Datalab.

## Credits

- [datalab-to/indra](https://github.com/datalab-to/indra) – official Indra OCR
- FastAPI + Uvicorn
