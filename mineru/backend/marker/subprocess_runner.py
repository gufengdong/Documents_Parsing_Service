from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from loguru import logger


def _sanitize_filename(filename: str) -> str:
    sanitized = re.sub(r'[/\\\.]{2,}|[/\\]', '', filename)
    sanitized = re.sub(r'[^\w.-]', '_', sanitized, flags=re.UNICODE)
    if sanitized.startswith('.'):
        sanitized = '_' + sanitized[1:]
    return sanitized or 'unnamed'


def _load_config(config_path: str | None) -> dict:
    if not config_path:
        return {}
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Marker conversion in a short-lived subprocess.")
    parser.add_argument("--input", required=True, help="Input PDF path.")
    parser.add_argument("--output-dir", required=True, help="Output directory path.")
    parser.add_argument("--md-name", default="doc.md", help="Markdown filename inside output dir.")
    parser.add_argument("--config", default=None, help="Path to a JSON config file for Marker.")
    args = parser.parse_args(argv)

    input_path = Path(args.input)
    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        return 2

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    images_dir = out_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    config = _load_config(args.config)

    try:
        from marker.converters.pdf import PdfConverter
        from marker.models import create_model_dict
        from marker.config.parser import ConfigParser
        from marker.output import text_from_rendered
    except ModuleNotFoundError:
        logger.exception(
            "Marker is not installed in this Python environment. "
            "Install it and ensure it's importable by the service runtime."
        )
        return 3
    except Exception:
        logger.exception("Failed importing Marker modules.")
        return 4

    try:
        config_parser = ConfigParser(config)
        converter = PdfConverter(
            config=config_parser.generate_config_dict(),
            artifact_dict=create_model_dict(),
            processor_list=config_parser.get_processors(),
            renderer=config_parser.get_renderer(),
            llm_service=config_parser.get_llm_service(),
        )
        rendered = converter(str(input_path))
        md_text, _, images = text_from_rendered(rendered)
    except Exception:
        logger.exception("Marker conversion failed.")
        return 5

    try:
        (out_dir / args.md_name).write_text(md_text, encoding="utf-8")
    except Exception:
        logger.exception("Failed writing markdown output.")
        return 6

    try:
        for image_id, image_obj in (images or {}).items():
            safe_id = _sanitize_filename(str(image_id))
            image_path = images_dir / f"{safe_id}.png"
            if hasattr(image_obj, "save"):
                image_obj.save(image_path)
            elif isinstance(image_obj, (bytes, bytearray)):
                image_path.write_bytes(image_obj)
            else:
                logger.warning(f"Unsupported image payload type for id={image_id}: {type(image_obj)}")
    except Exception:
        logger.exception("Failed writing extracted images.")
        return 7

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

