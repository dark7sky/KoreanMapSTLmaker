from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import box

from src.data_sources.validation import validate_area_overlaps_dem, validate_area_overlaps_vector


def _write_polygon(path: Path, polygon, crs: str = "EPSG:5179") -> None:
    gdf = gpd.GeoDataFrame({"id": [1]}, geometry=[polygon], crs=crs)
    gdf.to_file(path, driver="GeoJSON")


def test_validate_area_overlaps_vector_true(tmp_path):
    area_path = tmp_path / "area.geojson"
    building_path = tmp_path / "buildings.geojson"
    _write_polygon(area_path, box(1000.0, 1000.0, 1100.0, 1100.0))
    _write_polygon(building_path, box(1050.0, 1050.0, 1150.0, 1150.0))

    result = validate_area_overlaps_vector(
        area_path=area_path,
        vector_path=building_path,
        target_crs="EPSG:5179",
        source_label="building",
    )

    assert result.overlaps is True


def test_validate_area_overlaps_vector_false(tmp_path):
    area_path = tmp_path / "area.geojson"
    building_path = tmp_path / "buildings.geojson"
    _write_polygon(area_path, box(1000.0, 1000.0, 1100.0, 1100.0))
    _write_polygon(building_path, box(2000.0, 2000.0, 2100.0, 2100.0))

    result = validate_area_overlaps_vector(
        area_path=area_path,
        vector_path=building_path,
        target_crs="EPSG:5179",
        source_label="building",
    )

    assert result.overlaps is False


def test_validate_area_overlaps_dem_false(tmp_path):
    area_path = tmp_path / "area.geojson"
    _write_polygon(area_path, box(2000.0, 2000.0, 2100.0, 2100.0))

    result = validate_area_overlaps_dem(
        area_path=area_path,
        dem_path=Path("data/sample/dem.tif"),
        target_crs="EPSG:5179",
    )

    assert result.overlaps is False


def test_validate_area_requires_crs_fallback_when_missing(monkeypatch, tmp_path):
    area_path = tmp_path / "area.geojson"
    _write_polygon(area_path, box(1000.0, 1000.0, 1100.0, 1100.0))

    original_read = gpd.read_file

    def _read_without_crs(path):
        gdf = original_read(path)
        gdf = gdf.copy()
        gdf.crs = None
        return gdf

    monkeypatch.setattr("src.data_sources.validation.gpd.read_file", _read_without_crs)

    with pytest.raises(ValueError, match="CRS is missing"):
        validate_area_overlaps_vector(
            area_path=area_path,
            vector_path=area_path,
            target_crs="EPSG:5179",
        )
