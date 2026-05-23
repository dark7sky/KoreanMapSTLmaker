from pathlib import Path

import geopandas as gpd
from shapely.geometry import box

from src import buildings


class StubElevationSampler:
    samples = {}

    def __init__(self, dem_path, target_crs):
        self.dem_path = dem_path
        self.target_crs = target_crs
        self.closed = False

    def sample_one(self, x, y):
        return self.samples[(round(x, 6), round(y, 6))]

    def close(self):
        self.closed = True


def test_prepare_buildings_defaults_to_representative_base(monkeypatch):
    polygon = box(0, 0, 2, 2)
    monkeypatch.setattr(buildings, "load_buildings", lambda *_: _building_gdf(polygon))
    monkeypatch.setattr(buildings, "ElevationSampler", StubElevationSampler)
    StubElevationSampler.samples = {
        (1.0, 1.0): 14.0,
    }

    result = _prepare(polygon)

    assert len(result.buildings) == 1
    assert result.buildings[0].base_z == 4.0


def test_prepare_buildings_uses_min_sampled_base(monkeypatch):
    polygon = box(0, 0, 2, 2)
    monkeypatch.setattr(buildings, "load_buildings", lambda *_: _building_gdf(polygon))
    monkeypatch.setattr(buildings, "ElevationSampler", StubElevationSampler)
    StubElevationSampler.samples = {
        (1.0, 1.0): 20.0,
        (2.0, 0.0): 18.0,
        (2.0, 2.0): 15.0,
        (0.0, 2.0): 17.0,
        (0.0, 0.0): 19.0,
    }

    result = _prepare(polygon, base_elevation_mode="min")

    assert len(result.buildings) == 1
    assert result.buildings[0].base_z == 5.0


def test_prepare_buildings_uses_mean_sampled_base(monkeypatch):
    polygon = box(0, 0, 2, 2)
    monkeypatch.setattr(buildings, "load_buildings", lambda *_: _building_gdf(polygon))
    monkeypatch.setattr(buildings, "ElevationSampler", StubElevationSampler)
    StubElevationSampler.samples = {
        (1.0, 1.0): 20.0,
        (2.0, 0.0): 18.0,
        (2.0, 2.0): 15.0,
        (0.0, 2.0): 17.0,
        (0.0, 0.0): 30.0,
    }

    result = _prepare(polygon, base_elevation_mode="mean")

    assert len(result.buildings) == 1
    assert result.buildings[0].base_z == 10.0


def test_prepare_buildings_mean_ignores_missing_samples(monkeypatch):
    polygon = box(0, 0, 2, 2)
    monkeypatch.setattr(buildings, "load_buildings", lambda *_: _building_gdf(polygon))
    monkeypatch.setattr(buildings, "ElevationSampler", StubElevationSampler)
    StubElevationSampler.samples = {
        (1.0, 1.0): 20.0,
        (2.0, 0.0): float("nan"),
        (2.0, 2.0): 16.0,
        (0.0, 2.0): float("nan"),
        (0.0, 0.0): float("nan"),
    }

    result = _prepare(polygon, base_elevation_mode="mean")

    assert len(result.buildings) == 1
    assert result.buildings[0].base_z == 8.0


def _building_gdf(polygon):
    return gpd.GeoDataFrame([{"geometry": polygon}], geometry="geometry", crs="EPSG:3857")


def _prepare(polygon, base_elevation_mode="representative"):
    return buildings.prepare_buildings(
        Path("buildings.gpkg"),
        polygon,
        Path("dem.tif"),
        "EPSG:3857",
        None,
        10.0,
        3.0,
        6.0,
        0.0,
        base_elevation_mode=base_elevation_mode,
    )
