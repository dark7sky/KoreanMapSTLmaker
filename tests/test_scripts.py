import json
from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import Polygon

from scripts import create_sample_data, inspect_data


def test_create_sample_data_outputs_are_inspectable(tmp_path):
    dem_path = tmp_path / "dem.tif"
    buildings_path = tmp_path / "buildings.geojson"

    create_sample_data.create_dem(dem_path)
    create_sample_data.create_buildings(buildings_path)

    dem = inspect_data.inspect_raster(dem_path)
    buildings = inspect_data.inspect_vector(buildings_path, None)

    assert dem["exists"] is True
    assert dem["crs"] == "EPSG:5179"
    assert dem["width"] == 16
    assert dem["height"] == 16
    assert dem["count"] == 1
    assert dem["nodata"] == -9999.0

    assert buildings["exists"] is True
    assert buildings["crs"] == "EPSG:5179"
    assert buildings["feature_count"] == 3
    assert buildings["geometry_types"] == ["Polygon"]
    assert {"HEIGHT", "GRND_FLR"}.issubset(set(buildings["fields"]))


def test_inspect_vector_applies_fallback_crs_when_reader_reports_missing_crs(tmp_path, monkeypatch):
    area_path = tmp_path / "area.geojson"
    area_path.write_text(json.dumps({"type": "FeatureCollection", "features": []}), encoding="utf-8")
    gdf = gpd.GeoDataFrame(
        [{"name": "selected_area", "geometry": Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])}],
        crs=None,
    )
    monkeypatch.setattr(inspect_data.gpd, "read_file", lambda path: gdf)

    result = inspect_data.inspect_vector(area_path, "EPSG:4326")

    assert result["crs"] == "EPSG:4326"
    assert result["crs_was_missing"] is True
    assert result["feature_count"] == 1
    assert result["bounds"] == [0.0, 0.0, 1.0, 1.0]


def test_inspect_helpers_raise_for_missing_inputs(tmp_path):
    missing_path = Path(tmp_path / "missing.geojson")

    with pytest.raises(FileNotFoundError) as vector_error:
        inspect_data.inspect_vector(missing_path, None)
    assert vector_error.value.args == (missing_path,)

    with pytest.raises(FileNotFoundError) as raster_error:
        inspect_data.inspect_raster(tmp_path / "missing.tif")
    assert raster_error.value.args == (tmp_path / "missing.tif",)
