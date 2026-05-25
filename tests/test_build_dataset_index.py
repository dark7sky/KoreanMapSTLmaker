import json
import subprocess
import sys
from pathlib import Path

import geopandas as gpd
from shapely.geometry import Polygon

from scripts import build_dataset_index, create_sample_data


def test_build_index_for_dem_uses_relative_paths_and_metadata(tmp_path):
    dem_dir = tmp_path / "dem"
    dem_dir.mkdir()
    dem_path = dem_dir / "tile_a.tif"
    create_sample_data.create_dem(dem_path)

    index = build_dataset_index.build_index(root=tmp_path, kind="dem", target_crs="EPSG:5179")

    assert index["kind"] == "dem"
    assert index["dataset_count"] == 1
    entry = index["datasets"][0]
    assert entry["type"] == "dem"
    assert entry["path"] == "dem/tile_a.tif"
    assert entry["crs"] == "EPSG:5179"
    assert len(entry["bounds"]) == 4
    assert entry["coverage_bounds"] == entry["bounds"]
    assert entry["metadata"]["width"] == 16
    assert entry["metadata"]["height"] == 16
    assert entry["metadata"]["count"] == 1


def test_build_index_for_buildings_includes_feature_metadata(tmp_path):
    building_dir = tmp_path / "buildings"
    building_dir.mkdir()
    building_path = building_dir / "block.geojson"
    gdf = gpd.GeoDataFrame(
        [{"name": "b1", "height": 12.0, "geometry": Polygon([(0, 0), (5, 0), (5, 5), (0, 5)])}],
        crs="EPSG:4326",
    )
    gdf.to_file(building_path, driver="GeoJSON")

    index = build_dataset_index.build_index(root=tmp_path, kind="buildings", target_crs="EPSG:5179")

    assert index["kind"] == "buildings"
    assert index["dataset_count"] == 1
    entry = index["datasets"][0]
    assert entry["type"] == "buildings"
    assert entry["path"] == "buildings/block.geojson"
    assert entry["crs"] == "EPSG:4326"
    assert len(entry["bounds"]) == 4
    assert len(entry["coverage_bounds"]) == 4
    assert entry["metadata"]["feature_count"] == 1
    assert entry["metadata"]["geometry_types"] == ["Polygon"]
    assert set(entry["metadata"]["fields"]) == {"name", "height"}


def test_cli_writes_index_file(tmp_path):
    dem_path = tmp_path / "sample_dem.tif"
    create_sample_data.create_dem(dem_path)
    out_path = tmp_path / "dataset_index.json"

    subprocess.run(
        [
            sys.executable,
            str(Path("scripts") / "build_dataset_index.py"),
            "--root",
            str(tmp_path),
            "--kind",
            "dem",
            "--out",
            str(out_path),
            "--target-crs",
            "EPSG:5179",
        ],
        check=True,
    )

    index = json.loads(out_path.read_text(encoding="utf-8"))
    assert index["kind"] == "dem"
    assert index["target_crs"] == "EPSG:5179"
    assert index["dataset_count"] == 1
    assert index["datasets"][0]["path"] == "sample_dem.tif"
