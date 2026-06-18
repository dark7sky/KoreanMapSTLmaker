from __future__ import annotations

import os
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from web_api.core import WebApiError
from web_api.storage import JobStorage, StoredArtifact, create_job_storage


@dataclass(frozen=True)
class StoredFilePayload:
    job_id: str
    name: str
    size_bytes: int

    def as_dict(self) -> dict[str, object]:
        return {
            "job_id": self.job_id,
            "name": self.name,
            "size_bytes": self.size_bytes,
        }


def default_workspace() -> Path:
    return Path(os.environ.get("APP_WORKSPACE", ".")).expanduser().resolve()


def register_upload_path(
    job_id: str,
    source_path: str | Path,
    *,
    target_name: str | None = None,
    workspace: str | Path | None = None,
    storage_factory: Callable[[str | Path, str], JobStorage] = create_job_storage,
) -> dict[str, object]:
    storage = _storage_for(job_id, workspace, storage_factory)
    try:
        stored_path = storage.register_upload(Path(source_path), target_name)
    except FileNotFoundError as exc:
        raise WebApiError(400, f"Upload source file not found: {exc}") from exc
    except ValueError as exc:
        raise WebApiError(400, str(exc)) from exc
    return _stored_file_payload(storage, stored_path, storage.uploads_dir).as_dict()


def register_upload_stream(
    job_id: str,
    stream: BinaryIO,
    filename: str,
    *,
    target_name: str | None = None,
    workspace: str | Path | None = None,
    storage_factory: Callable[[str | Path, str], JobStorage] = create_job_storage,
) -> dict[str, object]:
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = Path(tmpdir) / "upload.bin"
        with temp_path.open("wb") as output:
            while True:
                chunk = stream.read(1024 * 1024)
                if not chunk:
                    break
                output.write(chunk)
        return register_upload_path(
            job_id,
            temp_path,
            target_name=target_name or filename,
            workspace=workspace,
            storage_factory=storage_factory,
        )


def list_artifacts(
    job_id: str,
    *,
    workspace: str | Path | None = None,
    storage_factory: Callable[[str | Path, str], JobStorage] = create_job_storage,
) -> dict[str, object]:
    storage = _storage_for(job_id, workspace, storage_factory)
    return {
        "job_id": storage.job_id,
        "artifacts": [_artifact_payload(storage.job_id, artifact) for artifact in storage.list_artifacts()],
    }


def resolve_artifact_download(
    job_id: str,
    artifact_path: str | Path,
    *,
    workspace: str | Path | None = None,
    storage_factory: Callable[[str | Path, str], JobStorage] = create_job_storage,
) -> Path:
    storage = _storage_for(job_id, workspace, storage_factory)
    try:
        resolved = storage.resolve_artifact(artifact_path)
    except ValueError as exc:
        raise WebApiError(400, str(exc)) from exc
    if not resolved.exists() or not resolved.is_file():
        raise WebApiError(404, f"Artifact not found: {artifact_path}")
    return resolved


def _storage_for(
    job_id: str,
    workspace: str | Path | None,
    storage_factory: Callable[[str | Path, str], JobStorage],
) -> JobStorage:
    try:
        return storage_factory(default_workspace() if workspace is None else workspace, job_id)
    except ValueError as exc:
        raise WebApiError(400, str(exc)) from exc


def _stored_file_payload(storage: JobStorage, path: Path, root: Path) -> StoredFilePayload:
    name = path.relative_to(root).as_posix()
    return StoredFilePayload(job_id=storage.job_id, name=name, size_bytes=path.stat().st_size)


def _artifact_payload(job_id: str, artifact: StoredArtifact) -> dict[str, object]:
    return {
        "job_id": job_id,
        "name": artifact.name,
        "size_bytes": artifact.size_bytes,
        "download_url": f"/jobs/{job_id}/artifacts/{artifact.name}",
    }
