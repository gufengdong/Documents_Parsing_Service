# Docling-Compatible MinerU Service

FastAPI wrapper that keeps docling serve–style endpoints while using MinerU as the parsing engine.

## Run
- Install deps (includes FastAPI/httpx): `pip install -e .[api]`
- Start server: `uvicorn projects.docling_compat.app:app --host 0.0.0.0 --port 8085`
- Concurrency: set `MAX_CONCURRENT_CONVERT` (default 1). If `MARKER_DEVICE` is GPU (e.g. `cuda`), the service clamps to 1 by default to avoid CUDA OOM (override with `ALLOW_GPU_MULTI_CONVERT=1`; real parallelism also needs `ALLOW_GPU_MULTI_WORKER=1`). **Note:** enabling multi-convert/multi-worker on a single GPU will also multiply **RAM** usage (each worker loads its own model copy); if you see RSS growth/OOM, prefer `MAX_CONCURRENT_CONVERT=1` + `CONVERT_WORKERS=1`, or run one server instance per GPU. With GPU multi-convert enabled, the service will auto-retry a CUDA OOM once by draining to an exclusive slot + restarting the pool with 1 worker (`CONVERT_OOM_RETRY=0` to disable). Optional weighted scheduling via `CONVERT_ADAPTIVE_WEIGHT=1`, `CONVERT_WEIGHT_PDF_PAGES_PER_SLOT`, `CONVERT_WEIGHT_MB_PER_SLOT`. To force RSS to drop after each task, set `CONVERT_SINGLE_USE_PROCESS=1` (spawns a fresh worker process per conversion; slower but avoids long-lived memory). For a middle ground, set `CONVERT_POOL_RECYCLE_TASKS=N` to recreate the process pool every N completed conversions.
- Stuck job guardrail: `CONVERT_WORKER_TIMEOUT_SECONDS` (default 300) hard-kills the conversion worker if it runs too long (set `0` to disable).
- Large PDF chunking: set `DOC_COMPAT_PDF_CHUNK_PAGES` (e.g. 50) to split long PDFs into page-range chunks and stitch markdown back together; `DOC_COMPAT_PDF_CHUNK_MAX_CHUNKS` (default 200) caps chunk count as a safety valve.
- Queueing note: uploads may still be received/saved concurrently by FastAPI; the conversion slot is acquired after the upload is saved. Extra requests will wait for a slot (you'll see `Convert queued ...` logs). To hard-cap concurrent HTTP requests, run uvicorn with `--limit-concurrency`.
- Office conversion: PPT/DOC/XLS inputs may fall back to LibreOffice. Set `SOFFICE_TIMEOUT_SECONDS` (default 0 = no timeout) to fail fast on stuck conversions; `SOFFICE_ISOLATE_PROFILE=1` (default) uses a temporary per-job LibreOffice profile to avoid stale lock issues.
- Response gzip: `DOC_COMPAT_GZIP=0` disables `GZipMiddleware` (can reduce peak RSS for very large JSON responses, especially when embedding base64 images).
- Embedded images: data URIs are encoded with `DOC_COMPAT_EMBED_IMAGE_FORMAT=auto` and downscaled by default (`DOC_COMPAT_EMBED_IMAGE_MAX_SIDE=2048`) to avoid runaway RSS; tune via `DOC_COMPAT_EMBED_IMAGE_*`.
- Marker page render DPI: marker renders page images for Layout/OCR and keeps them in memory during conversion. Defaults are 96 (lowres) / 192 (highres). Lower these to reduce RAM: `DOC_COMPAT_MARKER_LOWRES_DPI` / `DOC_COMPAT_MARKER_HIGHRES_DPI` (or `MARKER_LOWRES_IMAGE_DPI` / `MARKER_HIGHRES_IMAGE_DPI`).
- Marker progress logs: by default the service disables marker's `tqdm` progress bars to keep logs readable (`DOC_COMPAT_MARKER_DISABLE_TQDM=1`). Set `DOC_COMPAT_MARKER_DISABLE_TQDM=0` (or `MARKER_DISABLE_TQDM=0`) to re-enable progress bars.
- PDF backend preference: set `DOC_COMPAT_PDF_BACKEND=mineru` to try MinerU first for PDFs (marker is used as fallback). Default is `auto` (marker first, MinerU on marker failure).
- Model warmup: `MARKER_PRELOAD_MODELS=1` triggers a startup warmup subprocess; worker processes still load their own models (it does not “share” GPU memory across workers).
- Memory logging: set `DOC_COMPAT_LOG_RSS=1` to log per-stage RSS/HWM (includes worker processes; each log line prints pid).

## Verify (MVP)
```bash
curl -s -X POST "http://localhost:8085/v1/convert/file" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "files=@demo/pdfs/demo1.pdf;type=application/pdf" \
  -F "to_formats=md" \
  -F "image_export_mode=embedded" \
  -F "do_ocr=true" \
  -F "force_ocr=false" \
  -F "table_mode=accurate" \
  -F "do_table_structure=true" \
  -F "include_images=true" \
  -F "do_picture_description=false" \
| jq -r '.document.md_content' | head
```

```bash
curl -s -X POST "http://localhost:8085/v1/convert/source" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{"sources":[{"kind":"http","url":"https://arxiv.org/pdf/2501.17887"}],"options":{"to_formats":"md","image_export_mode":"embedded","do_ocr":true,"force_ocr":false,"do_table_structure":true,"include_images":true}}' \
| jq -r '.document.md_content' | head
```

## Behavior Notes
- Supported inputs: PDF, images, doc/docx/ppt/pptx/xls/xlsx/csv/html/epub/txt/md. `.md` is returned as-is; `.txt` is wrapped into a Markdown code block.
- Always returns `document.md_content`; other fields can be added later without breaking jq usage.
- `image_export_mode` falls back to embedded; non-md `to_formats` are accepted but md is always returned.
- OCR: `force_ocr` -> parse_method=ocr; `do_ocr=false` -> txt; otherwise auto.
- Tables: `do_table_structure` toggles MinerU table enable.
- Images: when `include_images=true`, md references are rewritten to base64 data URIs.
- Picture descriptions: set `do_picture_description=true` and pass `picture_description_api` (OpenAI-compatible). Failures are tolerated and leave “描述失败”.
- Global concurrency gate via `MAX_CONCURRENT_CONVERT`; per-request VLM concurrency via `picture_description_api.concurrency`.
