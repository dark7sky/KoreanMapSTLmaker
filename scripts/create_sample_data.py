from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import Polygon


ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DIR = ROOT / "data" / "sample"


def main() -> None:
    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    create_dem(SAMPLE_DIR / "dem.tif")
    create_buildings(SAMPLE_DIR / "buildings.geojson")
    print(f"Wrote sample data to {SAMPLE_DIR}")


def create_dem(path: Path) -> None:
    width = 16
    height = 16
    resolution = 10.0
    origin_x = 970.0
    origin_y = 1130.0

    yy, xx = np.mgrid[0:height, 0:width]
    data = 25.0 + xx * 0.8 + yy * 0.5 + np.sin(xx / 2.0) * 1.5
    transform = from_origin(origin_x, origin_y, resolution, resolution)

    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=1,
        dtype="float32",
        crs="EPSG:5179",
        transform=transform,
        nodata=-9999.0,
    ) as dataset:
        dataset.write(data.astype("float32"), 1)


def create_buildings(path: Path) -> None:
    buildings = gpd.GeoDataFrame(
        [
            {"HEIGHT": 18.0, "GRND_FLR": 6, "geometry": Polygon([(1015, 1015), (1040, 1015), (1040, 1045), (1015, 1045)])},
            {"HEIGHT": 0.0, "GRND_FLR": 4, "geometry": Polygon([(1060, 1020), (1090, 1020), (1090, 1055), (1060, 1055)])},
            {"HEIGHT": None, "GRND_FLR": None, "geometry": Polygon([(1035, 1070), (1070, 1070), (1070, 1095), (1035, 1095)])},
        ],
        crs="EPSG:5179",
    )
    buildings.to_file(path, driver="GeoJSON")


if __name__ == "__main__":
    main()
