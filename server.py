"""
Indra OCR API Server
Official Python indra-ocr + FastAPI
"""

import os
import tempfile
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal, Optional

import indra_ocr
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

# ---------- Config ----------
THREADS = int(os.getenv("INDRA_THREADS", "4"))
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "20"))
MAX_PAGES = int(os.getenv("MAX_PAGES", "50"))

# Global converter (loaded once at startup)
converter: Optional[indra_ocr.Converter] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global converter
    print(f"[startup] Loading Indra OCR (threads={THREADS})...")
    t0 = time.perf_counter()
    converter = indra_ocr.load(threads=THREADS)
    print(f"[startup] Model ready in {time.perf_counter() - t0:.1f}s")
    yield
    print("[shutdown] Cleaning up...")
    converter = None


app = FastAPI(
    title="Indra OCR API",
    description="Lightweight CPU OCR powered by official indra-ocr (Datalab). "
                "Supports images & PDFs → markdown / text / structured JSON.",
    version="1.0.0",
    lifespan=lifespan,
)


# ---------- Response Models ----------
class LineOut(BaseModel):
    box: list[float]
    text: str
    conf: float


class BlockOut(BaseModel):
    label: str
    bbox: list[float]
    text: str


class PageOut(BaseModel):
    page: int
    source: str
    markdown: Optional[str] = None
    text: str
    rotation: float = 0.0
    skew: float = 0.0
    lines: list[LineOut] = Field(default_factory=list)
    blocks: list[BlockOut] = Field(default_factory=list)
    timings: dict = Field(default_factory=dict)


class OCRResponse(BaseModel):
    status: str = "success"
    pages: list[PageOut]
    total_ms: float
    filename: str


# ---------- Helpers ----------
def _serialize_page(idx: int, page) -> PageOut:
    lines = []
    for line in getattr(page, "lines", []) or []:
        box = list(line.box) if hasattr(line, "box") else []
        conf = float(getattr(line, "conf", 0.0) or 0.0)
        lines.append(LineOut(box=box, text=str(line.text or ""), conf=conf))

    blocks = []
    for b in getattr(page, "blocks", []) or []:
        if isinstance(b, dict):
            blocks.append(
                BlockOut(
                    label=str(b.get("label", "")),
                    bbox=list(b.get("bbox", [])),
                    text=str(b.get("text", "")),
                )
            )
        else:
            blocks.append(
                BlockOut(
                    label=str(getattr(b, "label", "")),
                    bbox=list(getattr(b, "bbox", [])),
                    text=str(getattr(b, "text", "")),
                )
            )

    return PageOut(
        page=idx,
        source=str(getattr(page, "source", "ocr")),
        markdown=getattr(page, "markdown", None),
        text=str(getattr(page, "text", "") or ""),
        rotation=float(getattr(page, "rotation", 0.0) or 0.0),
        skew=float(getattr(page, "skew", 0.0) or 0.0),
        lines=lines,
        blocks=blocks,
        timings=dict(getattr(page, "timings", {}) or {}),
    )


ALLOWED_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif", ".pdf"}

# Magic-byte signatures for when filename has no extension (common with n8n)
MAGIC_MAP = [
    (b"%PDF", ".pdf"),
    (b"\x89PNG\r\n\x1a\n", ".png"),
    (b"\xff\xd8\xff", ".jpg"),          # JPEG
    (b"RIFF", ".webp"),                 # WebP starts with RIFF....WEBP
    (b"BM", ".bmp"),
    (b"II*\x00", ".tiff"),              # little-endian TIFF
    (b"MM\x00*", ".tiff"),              # big-endian TIFF
]

CONTENT_TYPE_MAP = {
    "application/pdf": ".pdf",
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/webp": ".webp",
    "image/bmp": ".bmp",
    "image/tiff": ".tiff",
    "image/x-tiff": ".tiff",
}


def detect_ext(filename: str, content: bytes, content_type: str | None) -> str:
    """Return a valid extension, or raise HTTPException."""
    # 1. From filename
    ext = Path(filename or "").suffix.lower()
    if ext in ALLOWED_EXT:
        return ext

    # 2. From Content-Type header
    if content_type:
        ct = content_type.split(";")[0].strip().lower()
        if ct in CONTENT_TYPE_MAP:
            return CONTENT_TYPE_MAP[ct]

    # 3. From magic bytes
    for magic, guessed in MAGIC_MAP:
        if content.startswith(magic):
            # WebP needs extra check
            if guessed == ".webp" and b"WEBP" not in content[:16]:
                continue
            return guessed

    raise HTTPException(
        status_code=400,
        detail=(
            f"Unsupported or unknown file type (filename={filename!r}, "
            f"content-type={content_type!r}). "
            f"Allowed: {sorted(ALLOWED_EXT)}"
        ),
    )


# ---------- Endpoints ----------
@app.get("/health")
async def health():
    return {
        "status": "ok" if converter is not None else "loading",
        "threads": THREADS,
        "version": getattr(indra_ocr, "__version__", "unknown"),
    }


@app.post("/ocr", response_model=OCRResponse)
async def ocr(
    file: UploadFile = File(..., description="Image or PDF file"),
    format: Literal["md", "text", "json"] = Form("md"),
    mode: Literal["auto", "ocr", "text"] = Form("auto"),
    max_pages: int = Form(MAX_PAGES),
):
    """
    Upload an image or PDF and get OCR result.

    - **format**: `md` (markdown), `text`, or `json` (full structured)
    - **mode**: `auto` (use PDF text layer when reliable), `ocr` (force OCR), `text` (text layer only)
    - **max_pages**: limit pages for multi-page PDFs
    """
    if converter is None:
        raise HTTPException(status_code=503, detail="Model not ready yet")

    content = await file.read()
    if len(content) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max {MAX_UPLOAD_MB} MB",
        )

    filename = file.filename or "upload"
    ext = detect_ext(filename, content, file.content_type)

    # Write to temp file (indra-ocr prefers path)
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    t0 = time.perf_counter()
    pages_out: list[PageOut] = []

    try:
        # Note: mode is set at load time in current API.
        # For simplicity we use the global converter (mode=auto by default).
        # If you need per-request mode, create a short-lived converter.
        for idx, page in converter.convert(tmp_path, max_pages=max_pages):
            pages_out.append(_serialize_page(idx, page))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR failed: {str(e)}")
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    total_ms = (time.perf_counter() - t0) * 1000

    # Optional: slim response when format is md/text
    if format == "md":
        for p in pages_out:
            p.lines = []
            p.blocks = []
    elif format == "text":
        for p in pages_out:
            p.markdown = None
            p.lines = []
            p.blocks = []

    return OCRResponse(
        pages=pages_out,
        total_ms=round(total_ms, 1),
        filename=filename,
    )


@app.post("/ocr/image")
async def ocr_image(
    file: UploadFile = File(...),
    format: Literal["md", "text", "json"] = Form("md"),
):
    """
    Convenience endpoint that only accepts images (no PDF).
    Same response shape as /ocr.
    """
    # Quick reject if filename clearly says PDF; otherwise /ocr will sniff content
    filename = file.filename or "image"
    if Path(filename).suffix.lower() == ".pdf":
        raise HTTPException(status_code=400, detail="Use /ocr for PDF files")
    return await ocr(file=file, format=format, mode="ocr", max_pages=1)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        workers=1,  # Important: single worker recommended with ONNX
    )
