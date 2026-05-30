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
    assert "HEIGHT" in result["suggested_fields"]["height"]
    assert "GRND_FLR" in result["suggested_fields"]["floor"]


def test_validate_real_dataset_missing_files_fails(tmp_path):
    result = validate_real_dataset(
        area_path=tmp_path / "missing_area.geojson",
        buildings_path=tmp_path / "missing_buildings.geojson",
        dem_path=tmp_path / "missing_dem.tif",
    )

    assert result["ok"] is False
    assert len(result["errors"]) == 3
    assert all(item["status"] == "fail" for item in result["checks"])


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

