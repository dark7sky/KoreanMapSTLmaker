from pathlib import Path

from app.auto_build_ui import default_auto_build_values, run_auto_build_from_values


def test_default_auto_build_values_use_sample_registry():
    values = default_auto_build_values()

    assert values["area_path"] == "data/sample/area.geojson"
    assert values["registry_path"] == "datasets.sample.json"
    assert values["terrain_boundary_mode"] == "polygon"
    assert values["dry_run"] is True


def test_run_auto_build_from_values_maps_inputs():
    values = default_auto_build_values()
    values.update(
        {
            "dataset_name": "named",
            "export_formats": ["stl", "glb", "stl"],
            "dry_run": False,
        }
    )
    seen = {}

    def fake_auto_build(**kwargs):
        seen.update(kwargs)
        return {
            "status": "built",
            "dry_run": False,
            "dataset": {"name": "named"},
            "selection": {"mode": "named"},
            "validation": {"ok": True, "errors": []},
            "build": {"outputs": {"stl": "output/model.stl"}},
            "command": "python make_model.py",
        }

    result = run_auto_build_from_values(values, auto_build_fn=fake_auto_build)

    assert result.ok is True
    assert seen["area_path"] == Path("data/sample/area.geojson")
    assert seen["registry_path"] == Path("datasets.sample.json")
    assert seen["dataset_name"] == "named"
    assert seen["export_formats"] == ("stl", "glb")
    assert seen["dry_run"] is False
    assert result.text_report is not None
    assert "Status: built" in result.text_report


def test_run_auto_build_from_values_reports_error():
    values = default_auto_build_values()

    def fake_auto_build(**_):
        raise RuntimeError("bad registry")

    result = run_auto_build_from_values(values, auto_build_fn=fake_auto_build)

    assert result.ok is False
    assert result.error == "bad registry"
