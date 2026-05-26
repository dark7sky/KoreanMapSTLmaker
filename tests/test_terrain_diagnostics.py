import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import box

from src.terrain import bounds_overlap, sample_terrain
from src.terrain import get_dem_info


def test_bounds_overlap_detects_separated_boxes():
    assert bounds_overlap([0, 0, 10, 10], [5, 5, 15, 15]) is True
    assert bounds_overlap([0, 0, 10, 10], [11, 11, 15, 15]) is False


def test_sample_terrain_reports_area_dem_no_overlap(tmp_path):
    dem_path = tmp_path / "dem.tif"
    data = np.ones((5, 5), dtype=np.float32)
    transform = from_origin(0, 5, 1, 1)

    with rasterio.open(
        dem_path,
        "w",
        driver="GTiff",
        height=data.shape[0],
        width=data.shape[1],
        count=1,
        dtype=data.dtype,
        crs="EPSG:3857",
        transform=transform,
        nodata=-9999,
    ) as dataset:
        dataset.write(data, 1)

    area = box(100, 100, 110, 110)

    with pytest.raises(ValueError, match="does not overlap the DEM"):
        sample_terrain(area, str(dem_path), "EPSG:3857", 1.0)


def test_sample_terrain_accepts_dem_crs_fallback(tmp_path):
    dem_path = tmp_path / "dem_without_crs.tif"
    data = np.arange(25, dtype=np.float32).reshape((5, 5))
    transform = from_origin(0, 5, 1, 1)

    with rasterio.open(
        dem_path,
        "w",
        driver="GTiff",
        height=data.shape[0],
        width=data.shape[1],
        count=1,
        dtype=data.dtype,
        transform=transform,
        nodata=-9999,
    ) as dataset:
        dataset.write(data, 1)

    area = box(0, 0, 4, 4)
    grid = sample_terrain(area, str(dem_path), "EPSG:3857", 1.0, dem_crs="EPSG:3857")
    info = get_dem_info(str(dem_path), "EPSG:3857", fallback_dem_crs="EPSG:3857")

    assert grid.valid.any()
    assert info.crs == "EPSG:3857"
