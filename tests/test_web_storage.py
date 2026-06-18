from pathlib import Path

import pytest

from web_api.storage import create_job_storage, workspace_jobs_dir


def test_create_job_storage_uses_workspace_local_directories(tmp_path):
    storage = create_job_storage(tmp_path, "job-123")

    assert storage.workspace == tmp_path.resolve()
    assert storage.job_dir == tmp_path.resolve() / ".web_api" / "jobs" / "job-123"
    assert storage.uploads_dir.exists()
    assert storage.artifacts_dir.exists()
    assert storage.job_dir.is_relative_to(tmp_path.resolve())


def test_register_upload_and_list_artifacts(tmp_path):
    storage = create_job_storage(tmp_path, "job-1")

    source = tmp_path / "source.txt"
    source.write_text("upload me", encoding="utf-8")

    uploaded = storage.register_upload(source)
    assert uploaded.read_text(encoding="utf-8") == "upload me"
    assert uploaded.parent == storage.uploads_dir

    artifact_one = tmp_path / "artifact-one.txt"
    artifact_one.write_text("first", encoding="utf-8")
    artifact_two = tmp_path / "nested" / "artifact-two.txt"
    artifact_two.parent.mkdir(parents=True, exist_ok=True)
    artifact_two.write_text("second", encoding="utf-8")

    stored_one = storage.register_artifact(artifact_one)
    stored_two = storage.register_artifact(artifact_two, "nested/result.txt")

    artifacts = storage.list_artifacts()

    assert [item.name for item in artifacts] == ["artifact-one.txt", "nested/result.txt"]
    assert [item.size_bytes for item in artifacts] == [5, 6]
    assert stored_one.read_text(encoding="utf-8") == "first"
    assert stored_two.read_text(encoding="utf-8") == "second"


def test_storage_rejects_traversal_and_absolute_paths(tmp_path):
    storage = create_job_storage(tmp_path, "job-safe")
    source = tmp_path / "source.txt"
    source.write_text("payload", encoding="utf-8")

    with pytest.raises(ValueError, match="job ids must be simple names"):
        create_job_storage(tmp_path, "../escape")

    with pytest.raises(ValueError, match="path traversal is not allowed"):
        storage.register_artifact(source, "../escape.txt")

    with pytest.raises(ValueError, match="absolute paths are not allowed"):
        storage.resolve_artifact(Path(tmp_path / "escape.txt"))


def test_workspace_jobs_dir_stays_under_workspace(tmp_path):
    jobs_dir = workspace_jobs_dir(tmp_path)

    assert jobs_dir == tmp_path.resolve() / ".web_api" / "jobs"
