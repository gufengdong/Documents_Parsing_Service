from __future__ import annotations

import asyncio
import io
import json
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

import pypdfium2 as pdfium
from loguru import logger

from mineru.utils.pdf_page_id import get_end_page_id


@dataclass(frozen=True)
class PageRange:
    start_page_id: int  # 0-based, inclusive
    end_page_id: int  # 0-based, inclusive


def get_pdf_page_count(pdf_bytes: bytes) -> int:
    pdf = pdfium.PdfDocument(pdf_bytes)
    try:
        return len(pdf)
    finally:
        pdf.close()


def slice_pdf_bytes(pdf_bytes: bytes, start_page_id: int, end_page_id: int | None) -> bytes:
    pdf = pdfium.PdfDocument(pdf_bytes)
    output_pdf = pdfium.PdfDocument.new()
    try:
        end_page_id = get_end_page_id(end_page_id, len(pdf))

        output_index = 0
        for page_index in range(start_page_id, end_page_id + 1):
            try:
                output_pdf.import_pages(pdf, pages=[page_index])
                output_index += 1
            except Exception as page_error:
                try:
                    output_pdf.del_page(output_index)
                except Exception:
                    pass
                logger.warning(f"Failed to import page {page_index}: {page_error}, skipping this page.")

        output_buffer = io.BytesIO()
        output_pdf.save(output_buffer)
        return output_buffer.getvalue()
    except Exception as e:
        logger.warning(f"Failed slicing PDF bytes ({start_page_id=}, {end_page_id=}): {e}, using original bytes.")
        return pdf_bytes
    finally:
        pdf.close()
        output_pdf.close()


def iter_page_ranges(
    *,
    start_page_id: int,
    end_page_id: int,
    pages_per_chunk: int,
) -> list[PageRange]:
    if pages_per_chunk <= 0:
        return [PageRange(start_page_id=start_page_id, end_page_id=end_page_id)]

    ranges: list[PageRange] = []
    cur = start_page_id
    while cur <= end_page_id:
        chunk_end = min(cur + pages_per_chunk - 1, end_page_id)
        ranges.append(PageRange(start_page_id=cur, end_page_id=chunk_end))
        cur = chunk_end + 1
    return ranges


def _rewrite_chunk_image_refs(markdown: str, rename_map: dict[str, str]) -> str:
    if not rename_map:
        return markdown

    rewritten = markdown
    for old_name, new_name in rename_map.items():
        rewritten = rewritten.replace(f"images/{old_name}", f"images/{new_name}")
        rewritten = rewritten.replace(f"./images/{old_name}", f"images/{new_name}")
        rewritten = rewritten.replace(f'src="images/{old_name}"', f'src="images/{new_name}"')
        rewritten = rewritten.replace(f"src='images/{old_name}'", f"src='images/{new_name}'")
        rewritten = rewritten.replace(f'src="./images/{old_name}"', f'src="images/{new_name}"')
        rewritten = rewritten.replace(f"src='./images/{old_name}'", f"src='images/{new_name}'")
    return rewritten


async def _run_marker_subprocess(
    *,
    input_pdf_path: Path,
    out_dir: Path,
    config_path: Path,
    timeout_s: int | None = None,
    extra_env: dict[str, str] | None = None,
) -> None:
    cmd = [
        sys.executable,
        "-m",
        "mineru.backend.marker.subprocess_runner",
        "--input",
        str(input_pdf_path),
        "--output-dir",
        str(out_dir),
        "--md-name",
        "doc.md",
        "--config",
        str(config_path),
    ]
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_s)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.communicate()
        raise TimeoutError(f"Marker subprocess timed out after {timeout_s}s: {' '.join(cmd)}")

    if proc.returncode != 0:
        stdout_text = (stdout or b"").decode("utf-8", errors="replace")[-4000:]
        stderr_text = (stderr or b"").decode("utf-8", errors="replace")[-4000:]
        raise RuntimeError(
            "Marker subprocess failed\n"
            f"  cmd: {' '.join(cmd)}\n"
            f"  exit: {proc.returncode}\n"
            f"  stdout_tail: {stdout_text}\n"
            f"  stderr_tail: {stderr_text}\n"
        )


async def convert_pdf_bytes_with_marker_subprocess(
    *,
    pdf_bytes: bytes,
    pdf_name: str,
    parse_dir: Path,
    start_page_id: int = 0,
    end_page_id: int | None = None,
    pages_per_chunk: int = 50,
    marker_config: dict | None = None,
    marker_subprocess_timeout_s: int | None = None,
    marker_semaphore: asyncio.Semaphore | None = None,
    keep_chunk_artifacts: bool = False,
) -> None:
    parse_dir.mkdir(parents=True, exist_ok=True)
    final_images_dir = parse_dir / "images"
    final_images_dir.mkdir(parents=True, exist_ok=True)

    total_pages = get_pdf_page_count(pdf_bytes)
    if total_pages <= 0:
        raise ValueError("Empty PDF (0 pages).")

    start_page_id = max(0, start_page_id)
    end_page_id = get_end_page_id(end_page_id, total_pages)
    if start_page_id > end_page_id:
        raise ValueError(f"Invalid page range: start_page_id={start_page_id} > end_page_id={end_page_id}")

    page_ranges = iter_page_ranges(
        start_page_id=start_page_id,
        end_page_id=end_page_id,
        pages_per_chunk=pages_per_chunk,
    )

    chunk_root_dir = parse_dir / "_marker_chunks"
    if chunk_root_dir.exists():
        shutil.rmtree(chunk_root_dir, ignore_errors=True)
    chunk_root_dir.mkdir(parents=True, exist_ok=True)

    config = marker_config or {
        "output_format": "markdown",
        "use_llm": False,
    }

    extra_env: dict[str, str] = {}
    convert_workers = os.getenv("MINERU_MARKER_CONVERT_WORKERS", "").strip()
    if convert_workers:
        extra_env["CONVERT_WORKERS"] = convert_workers
    vram_per_task = os.getenv("MINERU_MARKER_VRAM_PER_TASK", "").strip()
    if vram_per_task:
        extra_env["VRAM_PER_TASK"] = vram_per_task

    combined_parts: list[str] = []
    for idx, pr in enumerate(page_ranges):
        chunk_dir = chunk_root_dir / f"chunk_{idx:04d}_p{pr.start_page_id + 1:06d}-{pr.end_page_id + 1:06d}"
        chunk_dir.mkdir(parents=True, exist_ok=True)
        chunk_pdf_path = chunk_dir / "input.pdf"
        chunk_out_dir = chunk_dir / "out"
        chunk_out_dir.mkdir(parents=True, exist_ok=True)
        config_path = chunk_dir / "marker_config.json"
        config_path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")

        chunk_bytes = (
            pdf_bytes
            if pr.start_page_id == 0 and pr.end_page_id == total_pages - 1
            else slice_pdf_bytes(pdf_bytes, pr.start_page_id, pr.end_page_id)
        )
        chunk_pdf_path.write_bytes(chunk_bytes)

        try:
            if marker_semaphore is None:
                await _run_marker_subprocess(
                    input_pdf_path=chunk_pdf_path,
                    out_dir=chunk_out_dir,
                    config_path=config_path,
                    timeout_s=marker_subprocess_timeout_s,
                    extra_env=extra_env,
                )
            else:
                async with marker_semaphore:
                    await _run_marker_subprocess(
                        input_pdf_path=chunk_pdf_path,
                        out_dir=chunk_out_dir,
                        config_path=config_path,
                        timeout_s=marker_subprocess_timeout_s,
                        extra_env=extra_env,
                    )
        except Exception:
            logger.exception(f"Marker chunk conversion failed: {pdf_name} pages {pr.start_page_id}-{pr.end_page_id}")
            raise

        chunk_md_path = chunk_out_dir / "doc.md"
        if not chunk_md_path.exists():
            raise FileNotFoundError(f"Marker output markdown not found: {chunk_md_path}")
        chunk_md = chunk_md_path.read_text(encoding="utf-8", errors="replace")

        rename_map: dict[str, str] = {}
        chunk_images_dir = chunk_out_dir / "images"
        if chunk_images_dir.exists():
            for image_path in sorted(chunk_images_dir.glob("*")):
                if not image_path.is_file():
                    continue
                new_name = f"{idx:04d}_{image_path.name}"
                target = final_images_dir / new_name
                counter = 1
                while target.exists():
                    target = final_images_dir / f"{idx:04d}_{counter:03d}_{image_path.name}"
                    counter += 1
                shutil.move(str(image_path), str(target))
                rename_map[image_path.name] = target.name

        chunk_md = _rewrite_chunk_image_refs(chunk_md, rename_map)
        combined_parts.append(
            "\n\n".join(
                [
                    f"<!-- marker-chunk: {idx:04d} pages {pr.start_page_id + 1}-{pr.end_page_id + 1} -->",
                    chunk_md.strip(),
                ]
            )
        )

    out_md_path = parse_dir / f"{pdf_name}.md"
    out_md_path.write_text("\n\n".join(part for part in combined_parts if part).strip() + "\n", encoding="utf-8")

    if not keep_chunk_artifacts:
        shutil.rmtree(chunk_root_dir, ignore_errors=True)
