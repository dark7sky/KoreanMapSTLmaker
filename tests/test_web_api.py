import importlib
from pathlib import Path
import sys
import types

import pytest

from app.ui_state import default_form_values
from src.pipeline import BuildOptions
from web_api.core import WebApiError, build_from_payload, health_payload


def _sample_payload() -> dict[str, object]:
    values = default_form_values()
    values.update(
        {
            "area_path": "data/sample/area.geojson",
            "buildings_path": "data/sample/buildings.geojson",
            "dem_path": "data/sample/dem.tif",
            "out_path": "output/model.stl",
            "height_fields": "HEIGHT,BUILD_H",
            "floor_fields": ["FLOORS", "LEVELS"],
            "export_formats": ["stl", "obj", "stl"],
        }
    )
    return values


def test_health_payload():
    assert health_payload() == {"status": "ok"}


def test_build_from_payload_maps_options_and_calls_build():
    payload = _sample_payload()
    seen = {}

    def fake_build(options: BuildOptions) -> dict:
        seen["options"] = options
        return {"output": "output/model.stl", "faces": 12}

    result = build_from_payload(payload, build_fn=fake_build)

    assert result == {"output": "output/model.stl", "faces": 12}
    options = seen["options"]
    assert options.area_path == Path("data/sample/area.geojson")
    assert options.buildings_path == Path("data/sample/buildings.geojson")
    assert options.dem_path == Path("data/sample/dem.tif")
    assert options.out_path == Path("output/model.stl")
    assert options.height_fields == ("HEIGHT", "BUILD_H")
    assert options.floor_fields == ("FLOORS", "LEVELS")
    assert options.export_formats == ("stl", "obj")


def test_build_from_payload_translates_validation_errors():
    payload = _sample_payload()
    del payload["area_path"]

    with pytest.raises(WebApiError) as excinfo:
        build_from_payload(payload, build_fn=lambda _: {})

    assert excinfo.value.status_code == 422
    assert "Missing required field" in excinfo.value.detail


def test_build_from_payload_translates_build_failures():
    payload = _sample_payload()

    def fake_build(_: BuildOptions) -> dict:
        raise FileNotFoundError("data/sample/dem.tif")

    with pytest.raises(WebApiError) as excinfo:
        build_from_payload(payload, build_fn=fake_build)

    assert excinfo.value.status_code == 400
    assert "Input file not found" in excinfo.value.detail


def test_create_app_registers_routes_when_fastapi_is_available(monkeypatch):
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
        File=lambda *args, **kwargs: None,
        Form=lambda *args, **kwargs: None,
        HTTPException=type("HTTPException", (Exception,), {}),
        UploadFile=object,
    )
    fake_responses = types.SimpleNamespace(
        FileResponse=type("FileResponse", (), {}),
    )
    monkeypatch.setitem(sys.modules, "fastapi", fake_fastapi)
    monkeypatch.setitem(sys.modules, "fastapi.responses", fake_responses)

    module = importlib.import_module("web_api.app")
    module = importlib.reload(module)

    assert module.app is not None
    assert module.app.title == "MAP Web API"
    assert ("GET", "/health", "health") in module.app.routes
    assert ("POST", "/build", "build") in module.app.routes
    assert ("POST", "/jobs/{job_id}/uploads", "upload_file") in module.app.routes
    assert ("GET", "/jobs/{job_id}/artifacts", "artifacts") in module.app.routes
    assert ("GET", "/jobs/{job_id}/artifacts/{artifact_path:path}", "download_artifact") in module.app.routes
