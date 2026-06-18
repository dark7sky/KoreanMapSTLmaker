import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

from scripts.validate_real_dem import validate_real_dem


def test_validate_real_dem_tiny_geotiff_passes(tmp_path):
    dem_path = tmp_path / "tiny_dem.tif"
    _write_dem(dem_path, np.array([[10.0, 11.0], [12.0, 13.0]], dtype="float32"))

    result = validate_real_dem(
        dem_path=dem_path,
        target_crs="EPSG:5179",
        source_name="NGII test fixture",
        source_date="2026-01-15",
        license_name="Public",
    )

    assert result["ok"] is True
    assert result["errors"] == []
    assert result["source"]["name"] == "NGII test fixture"
    assert result["source"]["date"] == "2026-01-15"
    assert result["source"]["license"] == "Public"
    assert result["dem"]["crs"] == "EPSG:5179"
    assert result["dem"]["width"] == 2
    assert result["dem"]["height"] == 2
    assert result["dem"]["elevation"]["min"] == 10.0
    assert result["dem"]["elevation"]["max"] == 13.0
    assert any(item["name"] == "dem_elevation_stats" and item["status"] == "pass" for item in result["checks"])


def test_validate_real_dem_cli_writes_json_with_crs_warning(tmp_path):
    dem_path = tmp_path / "tiny_dem_4326.tif"
    report_path = tmp_path / "report.json"
    _write_dem(dem_path, np.array([[1, 2], [3, 4]], dtype="int16"), crs="EPSG:4326")

    completed = subprocess.run(
        [
            sys.executable,
            str(Path("scripts") / "validate_real_dem.py"),
            "--dem",
            str(dem_path),
            "--target-crs",
            "EPSG:5179",
            "--format",
            "json",
            "--json-out",
            str(report_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    terminal_payload = json.loads(completed.stdout)
    file_payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert terminal_payload["ok"] is True
    assert file_payload["dem"]["crs"] == "EPSG:4326"
    assert any(item["name"] == "dem_target_crs" and item["status"] == "warn" for item in file_payload["checks"])
    assert any("reproject" in step for step in file_payload["next_steps"])


def test_validate_real_dem_all_nodata_fails(tmp_path):
    dem_path = tmp_path / "nodata_dem.tif"
    _write_dem(
        dem_path,
        np.array([[-9999.0, -9999.0], [-9999.0, -9999.0]], dtype="float32"),
        nodata=-9999.0,
    )

    result = validate_real_dem(dem_path=dem_path, target_crs="EPSG:5179")

    assert result["ok"] is False
    assert result["dem"]["valid_cells"] == 0
    assert any(item["name"] == "dem_valid_elevation_samples" and item["status"] == "fail" for item in result["checks"])
    assert any(item["name"] == "dem_elevation_stats" and item["status"] == "fail" for item in result["checks"])


def _write_dem(
    path: Path,
    values: np.ndarray,
    *,
    crs: str = "EPSG:5179",
    nodata: float | None = None,
) -> None:
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=values.shape[0],
        width=values.shape[1],
        count=1,
        dtype=str(values.dtype),
        crs=crs,
        transform=from_origin(1000.0, 2000.0, 5.0, 5.0),
        nodata=nodata,
    ) as dataset:
        dataset.write(values, 1)
