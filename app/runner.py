import time
from dataclasses import dataclass
from typing import Callable

from src.pipeline import BuildOptions, build_model


@dataclass
class RunResult:
    ok: bool
    elapsed_seconds: float
    summary: dict | None = None
    error: str | None = None


def run_build(options: BuildOptions, build_fn: Callable[[BuildOptions], dict] = build_model) -> RunResult:
    started = time.perf_counter()
    try:
        summary = build_fn(options)
    except Exception as exc:  # pragma: no cover - branch tested with monkeypatch in caller flow
        return RunResult(ok=False, elapsed_seconds=time.perf_counter() - started, error=str(exc))
    return RunResult(ok=True, elapsed_seconds=time.perf_counter() - started, summary=summary)

