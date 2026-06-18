from __future__ import annotations

import json
import os
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.pipeline import BuildOptions, build_model
from web_api.core import WebApiError, build_from_payload
from web_api.storage import JobStorage, create_job_storage, workspace_jobs_dir

JOB_METADATA_NAME = "job.json"


def run_job_from_payload(
    payload: Mapping[str, Any],
    *,
    workspace: str | Path | None = None,
    build_fn: Callable[[BuildOptions], dict] = build_model,
    id_factory: Callable[[], str] | None = None,
) -> dict[str, Any]:
    build_payload = _build_payload(payload)
    job_id = _job_id(payload, id_factory)

    try:
        storage = create_job_storage(_default_workspace() if workspace is None else workspace, job_id)
    except ValueError as exc:
        raise WebApiError(422, str(exc)) from exc

    metadata: dict[str, Any] = {
        "job_id": storage.job_id,
        "status": "running",
        "created_at": _utc_now(),
        "updated_at": _utc_now(),
        "request": _jsonable(build_payload),
        "result": None,
        "error": None,
        "artifacts": [],
    }
    _write_metadata(storage.job_dir, metadata)

    try:
        result = build_from_payload(build_payload, build_fn=build_fn)
    except WebApiError as exc:
        metadata.update(
            {
                "status": "failed",
                "updated_at": _utc_now(),
                "error": {"status_code": exc.status_code, "detail": exc.detail},
                "artifacts": _artifact_payload(storage),
            }
        )
    else:
        metadata.update(
            {
                "status": "succeeded",
                "updated_at": _utc_now(),
                "result": _jsonable(result),
                "artifacts": _artifact_payload(storage),
            }
        )

    _write_metadata(storage.job_dir, metadata)
    return metadata


def get_job_status(job_id: str, *, workspace: str | Path | None = None) -> dict[str, Any]:
    try:
        storage = create_job_storage(_default_workspace() if workspace is None else workspace, job_id)
    except ValueError as exc:
        raise WebApiError(422, str(exc)) from exc

    metadata_path = storage.job_dir / JOB_METADATA_NAME
    if not metadata_path.exists():
        raise WebApiError(404, f"Job not found: {storage.job_id}")
    return json.loads(metadata_path.read_text(encoding="utf-8"))


def list_job_ids(*, workspace: str | Path | None = None) -> tuple[str, ...]:
    jobs_dir = workspace_jobs_dir(_default_workspace() if workspace is None else workspace)
    if not jobs_dir.exists():
        return ()
    return tuple(sorted(path.name for path in jobs_dir.iterdir() if (path / JOB_METADATA_NAME).is_file()))


def _job_id(payload: Mapping[str, Any], id_factory: Callable[[], str] | None) -> str:
    raw_job_id = payload.get("job_id")
    if raw_job_id is not None and str(raw_job_id).strip():
        return str(raw_job_id).strip()
    factory = id_factory if id_factory is not None else lambda: f"job-{uuid4().hex}"
    return str(factory()).strip()


def _build_payload(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    nested_payload = payload.get("payload")
    if isinstance(nested_payload, Mapping):
        return nested_payload
    return {key: value for key, value in payload.items() if key != "job_id"}


def _artifact_payload(storage: JobStorage) -> list[dict[str, Any]]:
    return [
        {
            "name": artifact.name,
            "uri": artifact.uri,
            "exists": artifact.exists,
            "size_bytes": artifact.size_bytes,
        }
        for artifact in storage.list_artifacts()
    ]


def _write_metadata(job_dir: Path, metadata: Mapping[str, Any]) -> None:
    job_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = job_dir / JOB_METADATA_NAME
    temporary_path = job_dir / f"{JOB_METADATA_NAME}.tmp"
    temporary_path.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
    temporary_path.replace(metadata_path)


def _jsonable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _default_workspace() -> Path:
    return Path(os.environ.get("APP_WORKSPACE", ".")).expanduser().resolve()
