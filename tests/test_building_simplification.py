from pathlib import Path

import geopandas as gpd
from shapely.geometry import Polygon, box

from src import buildings


class _StubElevationSampler:
    def __init__(self, dem_path, target_crs):
        self.dem_path = dem_path
        self.target_crs = target_crs

    def sample_one(self, x, y):
        return 10.0

    def close(self):
        return None


def test_prepare_buildings_keeps_default_geometry_without_simplification(monkeypatch):
    polygon = _jagged_rectangle()
    monkeypatch.setattr(buildings, "load_buildings", lambda *_: _building_gdf(polygon))
    monkeypatch.setattr(buildings, "ElevationSampler", _StubElevationSampler)

    result = _prepare(polygon, simplify_tolerance=0.0)

    assert len(result.buildings) == 1
    prepared = result.buildings[0].polygon
    assert prepared.equals(polygon)
    assert len(prepared.exterior.coords) == len(polygon.exterior.coords)


def test_prepare_buildings_simplifies_geometry_when_tolerance_is_positive(monkeypatch):
    polygon = _jagged_rectangle()
    monkeypatch.setattr(buildings, "load_buildings", lambda *_: _building_gdf(polygon))
    monkeypatch.setattr(buildings, "ElevationSampler", _StubElevationSampler)

    result = _prepare(polygon, simplify_tolerance=0.4)

    assert len(result.buildings) == 1
    simplified = result.buildings[0].polygon
    assert simplified.is_valid
    assert len(simplified.exterior.coords) < len(polygon.exterior.coords)


def _jagged_rectangle() -> Polygon:
    return Polygon(
        [
            (0.0, 0.0),
            (8.0, 0.0),
            (8.0, 0.2),
            (7.6, 0.2),
            (7.6, 0.5),
            (8.0, 0.5),
            (8.0, 0.9),
            (7.6, 0.9),
            (7.6, 1.2),
            (8.0, 1.2),
            (8.0, 8.0),
            (0.0, 8.0),
            (0.0, 0.0),
        ]
    )


def _building_gdf(polygon):
    return gpd.GeoDataFrame([{"geometry": polygon}], geometry="geometry", crs="EPSG:3857")


def _prepare(polygon, simplify_tolerance: float):
    return buildings.prepare_buildings(
        Path("buildings.gpkg"),
        box(-1.0, -1.0, 20.0, 20.0),
        Path("dem.tif"),
        "EPSG:3857",
        None,
        5.0,
        3.0,
        6.0,
        0.0,
        simplify_tolerance=simplify_tolerance,
    )
