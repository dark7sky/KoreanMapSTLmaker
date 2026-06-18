from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePath
from typing import Iterable


@dataclass(frozen=True)
class StoredArtifact:
    name: str
    path: Path
    exists: bool
    size_bytes: int

    @property
    def uri(self) -> str:
        return self.path.resolve().as_uri()


@dataclass(frozen=True)
class JobStorage:
    workspace: Path
    job_id: str
    job_dir: Path
    uploads_dir: Path
    artifacts_dir: Path

    def ensure(self) -> None:
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

    def register_upload(self, source_path: Path, target_name: str | None = None) -> Path:
        return self._copy_into_directory(source_path, self.uploads_dir, target_name)

    def register_artifact(self, source_path: Path, target_name: str | None = None) -> Path:
        return self._copy_into_directory(source_path, self.artifacts_dir, target_name)

    def resolve_artifact(self, relative_path: str | Path) -> Path:
        return _safe_join(self.artifacts_dir, relative_path)

    def list_artifacts(self) -> tuple[StoredArtifact, ...]:
        if not self.artifacts_dir.exists():
            return ()
        artifacts: list[StoredArtifact] = []
        for path in sorted(
            _iter_files(self.artifacts_dir),
            key=lambda item: item.relative_to(self.artifacts_dir).as_posix(),
        ):
            artifacts.append(
                StoredArtifact(
                    name=path.relative_to(self.artifacts_dir).as_posix(),
                    path=path,
                    exists=path.exists(),
                    size_bytes=path.stat().st_size,
                )
            )
        return tuple(artifacts)

    def _copy_into_directory(self, source_path: Path, destination_dir: Path, target_name: str | None) -> Path:
        source = Path(source_path)
        if not source.exists() or not source.is_file():
            raise FileNotFoundError(source)
        destination_dir.mkdir(parents=True, exist_ok=True)
        name = target_name if target_name is not None else source.name
        destination = _safe_join(destination_dir, name)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())
        return destination


def workspace_jobs_dir(workspace: str | Path) -> Path:
    return Path(workspace).expanduser().resolve() / ".web_api" / "jobs"


def create_job_storage(workspace: str | Path, job_id: str) -> JobStorage:
    workspace_path = Path(workspace).expanduser().resolve()
    try:
        safe_job_id = _safe_relative_name(job_id, allow_nested=False)
    except ValueError as exc:
        raise ValueError(f"job ids must be simple names: {job_id!r}") from exc
    jobs_dir = workspace_path / ".web_api" / "jobs"
    job_dir = _safe_join(jobs_dir, safe_job_id)
    storage = JobStorage(
        workspace=workspace_path,
        job_id=safe_job_id.as_posix(),
        job_dir=job_dir,
        uploads_dir=job_dir / "uploads",
        artifacts_dir=job_dir / "artifacts",
    )
    storage.ensure()
    return storage


def _safe_join(base_dir: Path, relative_path: str | Path) -> Path:
    base = Path(base_dir).expanduser().resolve()
    relative = _safe_relative_name(relative_path, allow_nested=True)
    candidate = (base / relative).resolve()
    if candidate == base or base in candidate.parents:
        return candidate
    raise ValueError(f"path escapes storage root: {relative_path!r}")


def _safe_relative_name(raw_value: str | Path, *, allow_nested: bool) -> Path:
    text = str(raw_value).strip()
    if not text:
        raise ValueError("path must not be empty")
    candidate = PurePath(text.replace("\\", "/"))
    if candidate.is_absolute() or candidate.drive:
        raise ValueError(f"absolute paths are not allowed: {raw_value!r}")
    parts = candidate.parts
    if any(part in {"..", ""} for part in parts):
        raise ValueError(f"path traversal is not allowed: {raw_value!r}")
    if not allow_nested and len(parts) != 1:
        raise ValueError(f"job ids must be simple names: {raw_value!r}")
    return Path(*parts)


def _iter_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if path.is_file():
            yield path
