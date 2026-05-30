import json
from pathlib import Path

import geopandas as gpd
import pytest

from scripts import fetch_buildings
from src.data_sources.base import Bounds
from src.data_sources.buildings import build_cache_key, fetch_buildings_geojson
from src.data_sources.vworld import VWorldGISBuildingProvider


def _fixture_feature_collection() -> dict:
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"HEIGHT": 12.5, "FLOORS": 4, "NAME": "A"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[126.0, 37.0], [126.001, 37.0], [126.001, 37.001], [126.0, 37.001], [126.0, 37.0]]],
                },
            }
        ],
    }


def test_vworld_request_url_contains_key_bbox_and_crs():
    provider = VWorldGISBuildingProvider(api_key="abc123", data_name="CUSTOM_LAYER")
    bounds = Bounds(126.0, 37.0, 126.1, 37.1)

    url = provider.build_request_url(bounds=bounds, crs="EPSG:4326")

    assert "key=abc123" in url
    assert "data=CUSTOM_LAYER" in url
    assert "BBOX%28126.0%2C37.0%2C126.1%2C37.1%29" in url
    assert "srsName=EPSG%3A4326" in url


def test_fetch_buildings_geojson_fixture_writes_geojson_metadata_and_cache(tmp_path):
    class FakeProvider:
        name = "fake-provider"

        def __init__(self) -> None:
            self.calls = 0

        def build_request_url(self, bounds: Bounds, crs: str) -> str:
            return f"https://example.com/buildings?bbox={bounds.as_vworld_bbox()}&crs={crs}"

        def fetch_feature_collection(self, bounds: Bounds, crs: str) -> dict:
            self.calls += 1
            return _fixture_feature_collection()

    provider = FakeProvider()
    bounds = Bounds(126.0, 37.0, 126.1, 37.1)
    out_path = tmp_path / "buildings.geojson"
    cache_dir = tmp_path / ".cache"

    fixture_response = {"response": {"result": _fixture_feature_collection()}}
    first = fetch_buildings_geojson(
        provider=provider,
        bounds=bounds,
        crs="EPSG:4326",
        out_path=out_path,
        cache_dir=cache_dir,
        fixture_response=fixture_response,
    )

    assert provider.calls == 0
    assert first["feature_count"] == 1
    assert first["source"] == "fixture"
    assert out_path.exists()
    metadata_path = Path(first["metadata_path"])
    assert metadata_path.exists()
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["provider"] == "fake-provider"
    assert metadata["source"] == "fixture"
    assert metadata["cache_key"] == build_cache_key("fake-provider", bounds, "EPSG:4326")
    assert metadata["suggested_height_fields"] == ["HEIGHT"]
    assert metadata["suggested_floor_fields"] == ["FLOORS"]
    assert first["suggested_height_fields"] == ["HEIGHT"]
    assert first["suggested_floor_fields"] == ["FLOORS"]

    gdf = gpd.read_file(out_path)
    assert len(gdf) == 1
    assert gdf.crs is not None


def test_fetch_buildings_geojson_uses_cache_when_available(tmp_path):
    class FakeProvider:
        name = "fake-provider"

        def __init__(self) -> None:
            self.calls = 0

        def build_request_url(self, bounds: Bounds, crs: str) -> str:
            return "https://example.com"

        def fetch_feature_collection(self, bounds: Bounds, crs: str) -> dict:
            self.calls += 1
            return _fixture_feature_collection()

    provider = FakeProvider()
    bounds = Bounds(126.0, 37.0, 126.1, 37.1)
    out_path = tmp_path / "buildings.geojson"
    cache_dir = tmp_path / ".cache"

    first = fetch_buildings_geojson(
        provider=provider,
        bounds=bounds,
        crs="EPSG:4326",
        out_path=out_path,
        cache_dir=cache_dir,
    )
    second = fetch_buildings_geojson(
        provider=provider,
        bounds=bounds,
        crs="EPSG:4326",
        out_path=out_path,
        cache_dir=cache_dir,
    )

    assert first["source"] == "network"
    assert second["source"] == "cache"
    assert provider.calls == 1


def test_fetch_buildings_cli_requires_key_without_fixture(tmp_path, monkeypatch):
    out_path = tmp_path / "buildings.geojson"
    monkeypatch.delenv("VWORLD_API_KEY", raising=False)
    monkeypatch.setattr(
        "sys.argv",
        ["fetch_buildings.py", "--bounds", "126", "37", "126.1", "37.1", "--out", str(out_path)],
    )

    with pytest.raises(SystemExit) as error:
        fetch_buildings.main()

    assert "VWORLD_API_KEY is required for live fetches" in str(error.value)


def test_fetch_buildings_cli_fixture_mode_runs_without_key(tmp_path, monkeypatch):
    fixture_path = tmp_path / "fixture.json"
    fixture_path.write_text(json.dumps(_fixture_feature_collection()), encoding="utf-8")
    out_path = tmp_path / "buildings.geojson"
    monkeypatch.delenv("VWORLD_API_KEY", raising=False)
    monkeypatch.setattr(
        "sys.argv",
        [
            "fetch_buildings.py",
            "--bounds",
            "126",
            "37",
            "126.1",
            "37.1",
            "--out",
            str(out_path),
            "--fixture-response",
            str(fixture_path),
        ],
    )

    fetch_buildings.main()

    assert out_path.exists()


def test_fetch_buildings_geojson_suggests_korean_and_common_field_names(tmp_path):
    class FakeProvider:
        name = "fake-provider"

        def build_request_url(self, bounds: Bounds, crs: str) -> str:
            return "https://example.com"

        def fetch_feature_collection(self, bounds: Bounds, crs: str) -> dict:
            return {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {
                            "\uac74\ubb3c\ub192\uc774": 30.2,
                            "\uc9c0\uc0c1\uce35\uc218": 12,
                            "BLDG_H": 28.1,
                        },
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [
                                [
                                    [126.0, 37.0],
                                    [126.001, 37.0],
                                    [126.001, 37.001],
                                    [126.0, 37.001],
                                    [126.0, 37.0],
                                ]
                            ],
                        },
                    }
                ],
            }

    result = fetch_buildings_geojson(
        provider=FakeProvider(),
        bounds=Bounds(126.0, 37.0, 126.1, 37.1),
        crs="EPSG:4326",
        out_path=tmp_path / "buildings.geojson",
        cache_dir=tmp_path / ".cache",
    )

    assert result["suggested_height_fields"] == ["BLDG_H", "\uac74\ubb3c\ub192\uc774"]
    assert result["suggested_floor_fields"] == ["\uc9c0\uc0c1\uce35\uc218"]
