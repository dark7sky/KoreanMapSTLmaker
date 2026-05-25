import geopandas as gpd
import pytest
from shapely.geometry import Point

from src import io


def test_load_area_missing_crs_suggests_area_flag(monkeypatch, tmp_path):
    path = tmp_path / "area.geojson"
    path.write_text("{}", encoding="utf-8")
    gdf = gpd.GeoDataFrame([{"geometry": Point(0, 0)}], geometry="geometry", crs=None)
    monkeypatch.setattr(io.gpd, "read_file", lambda *_: gdf)

    with pytest.raises(ValueError, match="--area-crs EPSG:4326"):
        io.load_area(path, "EPSG:5179", None)


def test_load_buildings_missing_crs_suggests_building_flag(monkeypatch, tmp_path):
    path = tmp_path / "buildings.geojson"
    path.write_text("{}", encoding="utf-8")
    gdf = gpd.GeoDataFrame([{"geometry": Point(0, 0)}], geometry="geometry", crs=None)
    monkeypatch.setattr(io.gpd, "read_file", lambda *_: gdf)

    with pytest.raises(ValueError, match="--building-crs"):
        io.load_buildings(path, "EPSG:5179", None)


def test_load_area_rejects_invalid_fallback_crs(monkeypatch, tmp_path):
    path = tmp_path / "area.geojson"
    path.write_text("{}", encoding="utf-8")
    gdf = gpd.GeoDataFrame([{"geometry": Point(0, 0)}], geometry="geometry", crs=None)
    monkeypatch.setattr(io.gpd, "read_file", lambda *_: gdf)

    with pytest.raises(ValueError, match="Invalid fallback CRS"):
        io.load_area(path, "EPSG:5179", "not-a-crs")
