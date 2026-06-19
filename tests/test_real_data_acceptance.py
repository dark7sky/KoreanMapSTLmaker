import json
from pathlib import Path

from scripts import real_data_acceptance


def _write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def _dataset_report(path: str = "downloads/buildings/real.geojson") -> dict:
    return {
        "ok": True,
        "area": {},
        "buildings": {"path": path},
        "dem": {},
        "checks": [],
        "dataset_manifest": {},
    }


def _dem_report(path: str = "downloads/dem/real.tif") -> dict:
    return {
        "ok": True,
        "dem": {"path": path},
        "source": {"name": "Real DEM", "license": "verified"},
        "checks": [],
    }


def test_validate_acceptance_passes_for_non_sample_reports(tmp_path):
    dataset_path = tmp_path / "dataset.json"
    dem_path = tmp_path / "dem.json"
    _write(dataset_path, _dataset_report())
    _write(dem_path, _dem_report())

    result = real_data_acceptance.validate_acceptance(
        dataset_report_path=dataset_path,
        dem_report_path=dem_path,
    )

    assert result["passed"] is True
    assert result["remaining_master_plan_items"] == []


def test_validate_acceptance_rejects_sample_reports_by_default(tmp_path):
    dataset_path = tmp_path / "dataset.json"
    dem_path = tmp_path / "dem.json"
    _write(dataset_path, _dataset_report("data/sample/buildings.geojson"))
    _write(dem_path, _dem_report("data/sample/dem.tif"))

    result = real_data_acceptance.validate_acceptance(
        dataset_report_path=dataset_path,
        dem_report_path=dem_path,
    )

    assert result["passed"] is False
    assert any(check["name"] == "dataset_report_not_sample" and not check["passed"] for check in result["checks"])


def test_validate_acceptance_rejects_windows_sample_paths(tmp_path):
    dataset_path = tmp_path / "dataset.json"
    dem_path = tmp_path / "dem.json"
    _write(dataset_path, _dataset_report(r"C:\repo\data\sample\buildings.geojson"))
    _write(dem_path, _dem_report(r"C:\repo\data\sample\dem.tif"))

    result = real_data_acceptance.validate_acceptance(
        dataset_report_path=dataset_path,
        dem_report_path=dem_path,
    )

    assert result["passed"] is False
    assert any("data/sample" in check["message"] for check in result["checks"] if not check["passed"])


def test_cli_writes_acceptance_report_with_sample_override(tmp_path):
    dataset_path = tmp_path / "dataset.json"
    dem_path = tmp_path / "dem.json"
    out_path = tmp_path / "acceptance.json"
    _write(dataset_path, _dataset_report("data/sample/buildings.geojson"))
    _write(dem_path, _dem_report("data/sample/dem.tif"))

    exit_code = real_data_acceptance.main(
        [
            "--dataset-report",
            str(dataset_path),
            "--dem-report",
            str(dem_path),
            "--out",
            str(out_path),
            "--allow-sample",
        ]
    )

    saved = json.loads(out_path.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert saved["passed"] is True
