from io import BytesIO

import pytest

from web_api.core import WebApiError
from web_api.files import (
    list_artifacts,
    register_upload_path,
    register_upload_stream,
    resolve_artifact_download,
)
from web_api.storage import create_job_storage


def test_register_upload_path_returns_relative_payload(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text("hello", encoding="utf-8")

    result = register_upload_path(
        "job-1",
        source,
        target_name="inputs/source.txt",
        workspace=tmp_path,
    )

    assert result == {
        "job_id": "job-1",
        "name": "inputs/source.txt",
        "size_bytes": 5,
    }
    assert (tmp_path / ".web_api" / "jobs" / "job-1" / "uploads" / "inputs" / "source.txt").read_text(
        encoding="utf-8"
    ) == "hello"


def test_register_upload_stream_uses_filename_when_target_name_is_missing(tmp_path):
    result = register_upload_stream("job-1", BytesIO(b"payload"), "input.geojson", workspace=tmp_path)

    assert result == {
        "job_id": "job-1",
        "name": "input.geojson",
        "size_bytes": 7,
    }


def test_list_artifacts_returns_download_urls(tmp_path):
    storage = create_job_storage(tmp_path, "job-1")
    source = tmp_path / "model.stl"
    source.write_text("solid model", encoding="utf-8")
    storage.register_artifact(source, "exports/model.stl")

    result = list_artifacts("job-1", workspace=tmp_path)

    assert result == {
        "job_id": "job-1",
        "artifacts": [
            {
                "job_id": "job-1",
                "name": "exports/model.stl",
                "size_bytes": 11,
                "download_url": "/jobs/job-1/artifacts/exports/model.stl",
            }
        ],
    }


def test_resolve_artifact_download_returns_existing_file(tmp_path):
    storage = create_job_storage(tmp_path, "job-1")
    source = tmp_path / "model.obj"
    source.write_text("mesh", encoding="utf-8")
    stored = storage.register_artifact(source, "exports/model.obj")

    assert resolve_artifact_download("job-1", "exports/model.obj", workspace=tmp_path) == stored


@pytest.mark.parametrize(
    ("action", "expected_status"),
    [
        (lambda tmp_path: register_upload_path("../escape", tmp_path / "source.txt", workspace=tmp_path), 400),
        (
            lambda tmp_path: register_upload_stream(
                "job-1",
                BytesIO(b"payload"),
                "../escape.txt",
                workspace=tmp_path,
            ),
            400,
        ),
        (lambda tmp_path: resolve_artifact_download("job-1", "../escape.txt", workspace=tmp_path), 400),
        (lambda tmp_path: resolve_artifact_download("job-1", "missing.stl", workspace=tmp_path), 404),
    ],
)
def test_file_helpers_raise_web_api_errors(tmp_path, action, expected_status):
    source = tmp_path / "source.txt"
    source.write_text("payload", encoding="utf-8")

    with pytest.raises(WebApiError) as excinfo:
        action(tmp_path)

    assert excinfo.value.status_code == expected_status
