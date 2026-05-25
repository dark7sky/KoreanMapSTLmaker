import geopandas as gpd
import pytest
from shapely.geometry import GeometryCollection, LineString, Point, Polygon

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


def test_repair_geometry_fixes_invalid_polygon():
    invalid = Polygon([(0, 0), (1, 1), (1, 0), (0, 1), (0, 0)])
    repaired = io._repair_geometry(invalid)

    assert repaired.is_valid
    assert repaired.geom_type in {"Polygon", "MultiPolygon"}
    assert repaired.area > 0


def test_repair_geometry_extracts_polygon_from_collection():
    polygon = Polygon([(0, 0), (2, 0), (2, 2), (0, 2), (0, 0)])
    collection = GeometryCollection([Point(5, 5), polygon])
    repaired = io._repair_geometry(collection)

    assert repaired.geom_type == "Polygon"
    assert repaired.equals(polygon)


def test_repair_geometry_returns_empty_for_non_polygonal_inputs():
    repaired = io._repair_geometry(LineString([(0, 0), (1, 1)]))

    assert repaired.is_empty
