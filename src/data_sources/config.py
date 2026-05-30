from __future__ import annotations

import os
from pathlib import Path


def parse_env_text(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        values[key] = value.strip()
    return values


def load_env_file(path: Path, *, override: bool = False, environ: dict[str, str] | None = None) -> dict[str, str]:
    target_environ = os.environ if environ is None else environ
    content = path.read_text(encoding="utf-8")
    parsed = parse_env_text(content)
    applied: dict[str, str] = {}
    for key, value in parsed.items():
        if override or key not in target_environ:
            target_environ[key] = value
            applied[key] = value
    return applied


def load_optional_env_file(
    path: Path,
    *,
    override: bool = False,
    environ: dict[str, str] | None = None,
) -> dict[str, str]:
    if not path.exists():
        return {}
    return load_env_file(path, override=override, environ=environ)
