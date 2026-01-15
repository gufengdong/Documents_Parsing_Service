#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_DIRS=("projects/docling_compat")

missing_so=()
deleted_count=0

for rel_dir in "${TARGET_DIRS[@]}"; do
  abs_dir="${ROOT_DIR}/${rel_dir}"
  if [[ ! -d "${abs_dir}" ]]; then
    continue
  fi

  while IFS= read -r -d '' file; do
    if [[ "$(basename "${file}")" == "__init__.py" ]]; then
      continue
    fi

    base="${file%.py}"
    if ls "${base}".*.so >/dev/null 2>&1; then
      rm -f "${file}"
      deleted_count=$((deleted_count + 1))
    else
      missing_so+=("${file}")
    fi
  done < <(find "${abs_dir}" -type f -name "*.py" -print0)
done

if (( ${#missing_so[@]} > 0 )); then
  printf "Missing compiled .so for %d file(s). Sources left intact:\n" "${#missing_so[@]}"
  printf " - %s\n" "${missing_so[@]}"
  exit 1
fi

echo "Removed ${deleted_count} Python source file(s)."
