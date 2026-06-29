import json
import geopandas as gpd
import pytest
from shapely.geometry import box

from app.quick_build import (
    create_area_from_center,
    create_quick_registry,
    sanitize_output_name,
    save_uploaded_file,
)


def test_create_area_from_center_writes_wgs84_polygon(tmp_path):
    output = tmp_path / "area.geojson"

    result = create_area_from_center(
        latitude=37.5665,
        longitude=126.9780,
        width_m=300,
        height_m=200,
        output_path=output,
    )

    area = gpd.read_file(output)
    assert len(area) == 1
    assert area.crs.to_epsg() == 4326
    assert result["area_km2"] == pytest.approx(0.06, rel=0.03)


def test_save_uploaded_file_removes_directory_components(tmp_path):
    saved = save_uploaded_file(
        name="../../terrain.tif",
        data=b"raster-bytes",
        directory=tmp_path,
        kind="dem",
    )

    assert saved == (tmp_path / "terrain.tif").resolve()
    assert saved.read_bytes() == b"raster-bytes"


def test_save_uploaded_file_rejects_unsupported_extension(tmp_path):
    with pytest.raises(ValueError, match="Unsupported building file"):
        save_uploaded_file(name="buildings.exe", data=b"bad", directory=tmp_path, kind="building")


def test_create_quick_registry_detects_height_and_floor_fields(tmp_path):
    area_path = tmp_path / "area.geojson"
    building_path = tmp_path / "buildings.geojson"
    dem_path = tmp_path / "terrain.tif"
    registry_path = tmp_path / "session" / "dataset.json"
    gpd.GeoDataFrame({"name": ["area"]}, geometry=[box(126.97, 37.56, 126.98, 37.57)], crs="EPSG:4326").to_file(
        area_path, driver="GeoJSON"
    )
    gpd.GeoDataFrame(
        {"HEIGHT": [12.0], "GRND_FLR": [4]},
        geometry=[box(126.972, 37.562, 126.974, 37.564)],
        crs="EPSG:4326",
    ).to_file(building_path, driver="GeoJSON")
    dem_path.write_bytes(b"placeholder")

    registry = create_quick_registry(
        area_path=area_path,
        dem_path=dem_path,
        buildings_path=building_path,
        registry_path=registry_path,
    )

    entry = registry["datasets"][0]
    assert entry["height_fields"] == ["HEIGHT"]
    assert entry["floor_fields"] == ["GRND_FLR"]
    assert len(entry["coverage_bounds"]) == 4
    json.dumps(registry)


def test_sanitize_output_name_is_filesystem_safe():
    assert sanitize_output_name(" 서울 모델 01 ") == "서울_모델_01"
    assert sanitize_output_name("my/model:01") == "my_model_01"
