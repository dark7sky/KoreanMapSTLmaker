import numpy as np
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import box

import src.terrain
from src.terrain import ElevationSampler, sample_terrain


def test_sample_terrain_defaults_to_nearest(monkeypatch):
    captured = {"method": None}

    class StubSampler:
        nodata = None
        dem_crs = "EPSG:3857"

        def __init__(self, *args, **kwargs):
            pass

        def close(self):
            return None

        def bounds_in_target_crs(self):
            return [0.0, 0.0, 1.0, 1.0]

        def sample_many(self, points, method="nearest"):
            captured["method"] = method
            return np.array([1.0, 2.0, 3.0, 4.0], dtype=float)

    monkeypatch.setattr(src.terrain, "ElevationSampler", StubSampler)
    sample_terrain(box(0.0, 0.0, 1.0, 1.0), "dem.tif", "EPSG:3857", 1.0)
    assert captured["method"] == "nearest"


def test_elevation_sampler_bilinear_interpolates_tiny_raster(tmp_path):
    dem_path = tmp_path / "dem.tif"
    data = np.array([[0.0, 10.0], [20.0, 30.0]], dtype=np.float32)
    transform = from_origin(0.0, 2.0, 1.0, 1.0)
    with rasterio.open(
        dem_path,
        "w",
        driver="GTiff",
        height=2,
        width=2,
        count=1,
        dtype=data.dtype,
        crs="EPSG:3857",
        transform=transform,
        nodata=-9999.0,
    ) as dataset:
        dataset.write(data, 1)

    sampler = ElevationSampler(str(dem_path), "EPSG:3857")
    try:
        values = sampler.sample_many([(1.0, 1.0)], method="bilinear")
    finally:
        sampler.close()

    # (1.0, 1.0) is the center point between four cell centers.
    np.testing.assert_allclose(values, np.array([15.0]))
