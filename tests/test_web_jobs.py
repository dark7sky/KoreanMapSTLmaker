import importlib
import sys
import types
from pathlib import Path

import pytest

from app.ui_state import default_form_values
from src.pipeline import BuildOptions
from web_api.core import WebApiError
from web_api.jobs import get_job_status, list_job_ids, run_job_from_payload


def _sample_payload() -> dict[str, object]:
    values = default_form_values()
    values.update(
        {
            "area_path": "data/sample/area.geojson",
            "buildings_path": "data/sample/buildings.geojson",
            "dem_path": "data/sample/dem.tif",
            "out_path": "output/model.stl",
        }
    )
    return values


def test_run_job_from_payload_persists_success_metadata(tmp_path):
    seen = {}

    def fake_build(options: BuildOptions) -> dict:
        seen["options"] = options
        return {"output": str(options.out_path), "faces": 12}

    metadata = run_job_from_payload(
        {"job_id": "job-123", "payload": _sample_payload()},
        workspace=tmp_path,
        build_fn=fake_build,
    )

    assert metadata["job_id"] == "job-123"
    assert metadata["status"] == "succeeded"
    assert metadata["result"] == {"output": str(Path("output/model.stl")), "faces": 12}
    assert metadata["error"] is None
    assert seen["options"].out_path == Path("output/model.stl")

    persisted = get_job_status("job-123", workspace=tmp_path)
    assert persisted == metadata
    assert list_job_ids(workspace=tmp_path) == ("job-123",)
    assert (tmp_path / ".web_api" / "jobs" / "job-123" / "job.json").exists()


def test_run_job_from_payload_persists_failed_build(tmp_path):
    payload = _sample_payload()
    del payload["area_path"]

    metadata = run_job_from_payload(
        {"job_id": "bad-build", "payload": payload},
        workspace=tmp_path,
        build_fn=lambda _: {},
    )

    assert metadata["status"] == "failed"
    assert metadata["result"] is None
    assert metadata["error"]["status_code"] == 422
    assert "Missing required field" in metadata["error"]["detail"]
    assert get_job_status("bad-build", workspace=tmp_path)["status"] == "failed"


def test_run_job_from_payload_generates_safe_job_id(tmp_path):
    metadata = run_job_from_payload(
        _sample_payload(),
        workspace=tmp_path,
        build_fn=lambda _: {"ok": True},
        id_factory=lambda: "job-generated",
    )

    assert metadata["job_id"] == "job-generated"
    assert get_job_status("job-generated", workspace=tmp_path)["result"] == {"ok": True}


def test_job_api_rejects_unsafe_or_missing_ids(tmp_path):
    with pytest.raises(WebApiError) as excinfo:
        run_job_from_payload(
            {"job_id": "../escape", "payload": _sample_payload()},
            workspace=tmp_path,
            build_fn=lambda _: {},
        )

    assert excinfo.value.status_code == 422

    with pytest.raises(WebApiError) as missing:
        get_job_status("missing", workspace=tmp_path)

    assert missing.value.status_code == 404


def test_create_app_registers_job_routes_when_fastapi_is_available(monkeypatch):
    class FakeFastAPI:
        def __init__(self, title: str):
            self.title = title
            self.routes = []

        def get(self, path: str):
            def decorator(func):
                self.routes.append(("GET", path, func.__name__))
                return func

            return decorator

        def post(self, path: str):
            def decorator(func):
                self.routes.append(("POST", path, func.__name__))
                return func

            return decorator

    fake_fastapi = types.SimpleNamespace(
        FastAPI=FakeFastAPI,
        HTTPException=type("HTTPException", (Exception,), {}),
    )
    monkeypatch.setitem(sys.modules, "fastapi", fake_fastapi)
    monkeypatch.delitem(sys.modules, "fastapi.responses", raising=False)

    module = importlib.import_module("web_api.app")
    module = importlib.reload(module)

    assert module.app is not None
    assert ("POST", "/jobs", "run_job") in module.app.routes
    assert ("GET", "/jobs/{job_id}", "job_status") in module.app.routes
