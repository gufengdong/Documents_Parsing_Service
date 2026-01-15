#!/usr/bin/env python3
from pathlib import Path

from setuptools import Extension, setup
from Cython.Build import cythonize

SOURCE_DIRS = ["projects/docling_compat"]
ROOT_DIR = Path(__file__).resolve().parents[1]


def collect_extensions() -> list[Extension]:
    extensions = []
    for rel_dir in SOURCE_DIRS:
        base_dir = ROOT_DIR / rel_dir
        if not base_dir.exists():
            continue
        for path in base_dir.rglob("*.py"):
            if path.name == "__init__.py":
                continue
            rel_path = path.relative_to(ROOT_DIR)
            module_name = ".".join(rel_path.with_suffix("").parts)
            extensions.append(Extension(module_name, [str(rel_path)]))
    return extensions


extensions = collect_extensions()
if not extensions:
    raise SystemExit("No sources found to cythonize.")

setup(
    ext_modules=cythonize(
        extensions,
        compiler_directives={
            "language_level": "3",
            "binding": True,
            "embedsignature": True,
            "annotation_typing": False,
        },
    )
)
