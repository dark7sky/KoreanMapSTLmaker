import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.validate_real_dataset import validate_real_dataset


def test_validate_real_dataset_with_sample_inputs_passes():
    result = validate_real_dataset(
        area_path=Path("data/sample/area.geojson"),
        buildings_path=Path("data/sample/buildings.geojson"),
        dem_path=Path("data/sample/dem.tif"),
        target_crs="EPSG:5179",
    )

    assert result["ok"] is True
    assert result["errors"] == []
    assert result["checks"]
    assert any(item["name"] == "area_buildings_overlap" and item["status"] == "pass" for item in result["checks"])
    assert any(item["name"] == "area_dem_overlap" and item["status"] == "pass" for item in result["checks"])
    assert any(item["name"] == "buildings_fixture_manifest" and item["status"] == "pass" for item in result["checks"])
    assert "HEIGHT" in result["suggested_fields"]["height"]
    assert "GRND_FLR" in result["suggested_fields"]["floor"]
    assert result["dataset_manifest"]["schema"] == "real_dataset_validation_manifest_v1"
    building_manifest = result["dataset_manifest"]["inputs"]["buildings"]
    assert building_manifest["path"].endswith("data\\sample\\buildings.geojson") or building_manifest["path"].endswith(
        "data/sample/buildings.geojson"
    )
    assert building_manifest["size_bytes"] > 0
    assert len(building_manifest["sha256"]) == 64


def test_validate_real_dataset_missing_files_fails(tmp_path):
    result = validate_real_dataset(
        area_path=tmp_path / "missing_area.geojson",
        buildings_path=tmp_path / "missing_buildings.geojson",
        dem_path=tmp_path / "missing_dem.tif",
    )

    assert result["ok"] is False
    assert len(result["errors"]) == 3
    assert all(item["status"] == "fail" for item in result["checks"])
    assert result["dataset_manifest"]["inputs"]["buildings"]["sha256"] is None


def test_validate_real_dataset_area_dem_overlap_fail(tmp_path):
    area_path = tmp_path / "area.geojson"
    area_path.write_text(
        '{"type":"FeatureCollection","features":[{"type":"Feature","properties":{},"geometry":{"type":"Polygon","coordinates":[[[0,0],[0,1],[1,1],[1,0],[0,0]]]}}]}',
        encoding="utf-8",
    )
    result = validate_real_dataset(
        area_path=area_path,
        buildings_path=Path("data/sample/buildings.geojson"),
        dem_path=Path("data/sample/dem.tif"),
        area_crs="EPSG:4326",
        target_crs="EPSG:5179",
    )

    assert result["ok"] is False
    assert any(item["name"] == "area_dem_overlap" and item["status"] == "fail" for item in result["checks"])


def test_validate_real_dataset_writes_standalone_manifest(tmp_path):
    manifest_path = tmp_path / "real_dataset_manifest.json"

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/validate_real_dataset.py",
            "--area",
            "data/sample/area.geojson",
            "--buildings",
            "data/sample/buildings.geojson",
            "--dem",
            "data/sample/dem.tif",
            "--manifest-out",
            str(manifest_path),
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    report = json.loads(completed.stdout)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert report["ok"] is True
    assert manifest == report["dataset_manifest"]
    assert set(manifest["inputs"]) == {"area", "buildings", "dem"}


def test_validate_real_dataset_reports_missing_shp_sidecars(tmp_path):
    building_path = tmp_path / "buildings.shp"
    building_path.write_bytes(b"not a valid shapefile")

    result = validate_real_dataset(
        area_path=tmp_path / "missing_area.geojson",
        buildings_path=building_path,
        dem_path=tmp_path / "missing_dem.tif",
    )

    assert result["ok"] is False
    assert result["dataset_manifest"]["inputs"]["buildings"]["sidecars"][".shp"]["exists"] is True
    assert result["dataset_manifest"]["inputs"]["buildings"]["sidecars"][".shx"]["exists"] is False
    assert any(
        item["name"] == "buildings_shp_required_sidecars"
        and item["status"] == "fail"
        and ".shx" in item["message"]
        for item in result["checks"]
    )
