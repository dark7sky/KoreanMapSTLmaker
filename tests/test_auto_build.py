import json
from pathlib import Path

from scripts import auto_build
from src.pipeline import BuildOptions


def _write_registry(path: Path, *, dem: str | None = None, buildings: str | None = None) -> None:
    dem = dem or str(Path("data/sample/dem.tif").resolve())
    buildings = buildings or str(Path("data/sample/buildings.geojson").resolve())
    path.write_text(
        json.dumps(
            {
                "datasets": [
                    {
                        "name": "sample_auto",
                        "area": "data/sample/area.geojson",
                        "dem": dem,
                        "buildings": buildings,
                        "coverage_bounds": [990.0, 990.0, 1110.0, 1110.0],
                        "target_crs": "EPSG:5179",
                        "height_fields": ["HEIGHT"],
                        "floor_fields": ["GRND_FLR"],
                        "building_base_mode": "representative",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )


def test_auto_build_selects_validates_and_runs_build(tmp_path):
    registry_path = tmp_path / "datasets.json"
    _write_registry(registry_path)
    seen = {}

    def fake_build(options: BuildOptions) -> dict:
        seen["options"] = options
        return {"output": str(options.out_path), "faces": 42}

    report = auto_build.auto_build(
        area_path=Path("data/sample/area.geojson"),
        registry_path=registry_path,
        output_dir=tmp_path / "output",
        output_name="chosen",
        export_formats=("stl", "glb"),
        preview=True,
        build_fn=fake_build,
    )

    assert report["status"] == "built"
    assert report["dataset"]["name"] == "sample_auto"
    assert report["validation"]["ok"] is True
    assert report["build"] == {"output": str((tmp_path / "output" / "chosen.stl").resolve()), "faces": 42}
    options = seen["options"]
    assert options.area_path == Path("data/sample/area.geojson")
    assert options.out_path == (tmp_path / "output" / "chosen.stl").resolve()
    assert options.export_formats == ("stl", "glb")
    assert options.height_fields == ("HEIGHT",)
    assert options.floor_fields == ("GRND_FLR",)
    assert options.terrain_boundary_mode == "polygon"
    assert "--terrain-boundary-mode polygon" in report["command"]


def test_auto_build_dry_run_does_not_call_build(tmp_path):
    registry_path = tmp_path / "datasets.json"
    _write_registry(registry_path)

    def fail_build(_: BuildOptions) -> dict:
        raise AssertionError("dry run should not build")

    report = auto_build.auto_build(
        area_path=Path("data/sample/area.geojson"),
        registry_path=registry_path,
        output_dir=tmp_path / "output",
        dry_run=True,
        build_fn=fail_build,
    )

    assert report["status"] == "validated"
    assert report["build"] is None
    assert report["validation"]["ok"] is True


def test_auto_build_stops_when_validation_fails_without_force(tmp_path):
    registry_path = tmp_path / "datasets.json"
    _write_registry(registry_path, dem="missing_dem.tif")

    report = auto_build.auto_build(
        area_path=Path("data/sample/area.geojson"),
        registry_path=registry_path,
        output_dir=tmp_path / "output",
        build_fn=lambda _: {"should": "not run"},
    )

    assert report["status"] == "validation_failed"
    assert report["validation"]["ok"] is False
    assert report["build"] is None


def test_auto_build_cli_writes_summary_for_dry_run(tmp_path):
    registry_path = tmp_path / "datasets.json"
    summary_path = tmp_path / "auto_summary.json"
    _write_registry(registry_path)

    exit_code = auto_build.main(
        [
            "--area",
            "data/sample/area.geojson",
            "--registry",
            str(registry_path),
            "--output-dir",
            str(tmp_path / "output"),
            "--dry-run",
            "--summary-out",
            str(summary_path),
        ]
    )

    assert exit_code == 0
    saved = json.loads(summary_path.read_text(encoding="utf-8"))
    assert saved["status"] == "validated"
    assert saved["dataset"]["name"] == "sample_auto"


def test_format_text_report_summarizes_dry_run():
    report = {
        "status": "validated",
        "dry_run": True,
        "dataset": {"name": "sample_auto"},
        "selection": {"mode": "overlap", "best_match": {"area_overlap_ratio": 1.0}},
        "validation": {"ok": True, "errors": []},
        "build": None,
        "command": "python make_model.py --area area.geojson",
    }

    text = auto_build.format_text_report(report)

    assert "Status: validated" in text
    assert "Dataset: sample_auto" in text
    assert "Validation: PASS" in text
    assert "Build: not run" in text
    assert "python make_model.py" in text


def test_format_text_report_lists_build_outputs():
    report = {
        "status": "built",
        "dry_run": False,
        "dataset": {"name": "sample_auto"},
        "selection": {"mode": "named"},
        "validation": {"ok": True, "errors": []},
        "build": {
            "outputs": {"stl": "output/model.stl", "glb": "output/model.glb"},
            "preview": "output/model_preview.html",
            "summary": "output/model_summary.json",
        },
        "command": "python make_model.py --area area.geojson",
    }

    text = auto_build.format_text_report(report)

    assert "Outputs:" in text
    assert "stl: output/model.stl" in text
    assert "Preview: output/model_preview.html" in text
