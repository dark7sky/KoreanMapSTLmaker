import io
import json
from urllib.error import HTTPError, URLError

import pytest

from src.data_sources.base import Bounds
from src.data_sources.vworld import VWorldGISBuildingProvider


class _FakeHTTPResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return None


def _feature(name: str) -> dict:
    return {
        "type": "Feature",
        "properties": {"NAME": name},
        "geometry": {
            "type": "Point",
            "coordinates": [126.0, 37.0],
        },
    }


def test_build_request_url_includes_page_and_size():
    provider = VWorldGISBuildingProvider(api_key="abc123", page_size=50)
    bounds = Bounds(126.0, 37.0, 126.1, 37.1)

    url = provider.build_request_url(bounds=bounds, crs="EPSG:4326", page=3, page_size=25)

    assert "page=3" in url
    assert "size=25" in url
    assert "key=abc123" in url


def test_fetch_feature_collection_aggregates_pages(monkeypatch):
    provider = VWorldGISBuildingProvider(api_key="abc123", page_size=2, max_pages=5)
    bounds = Bounds(126.0, 37.0, 126.1, 37.1)
    urls: list[str] = []

    page_payloads = [
        {"type": "FeatureCollection", "features": [_feature("A"), _feature("B")]},
        {"type": "FeatureCollection", "features": [_feature("C")]},
    ]

    def fake_urlopen(url: str, timeout: int):
        urls.append(url)
        return _FakeHTTPResponse(page_payloads[len(urls) - 1])

    monkeypatch.setattr("src.data_sources.vworld.urlopen", fake_urlopen)

    merged = provider.fetch_feature_collection(bounds=bounds, crs="EPSG:4326")

    assert merged["type"] == "FeatureCollection"
    assert [f["properties"]["NAME"] for f in merged["features"]] == ["A", "B", "C"]
    assert len(urls) == 2
    assert "page=1" in urls[0]
    assert "page=2" in urls[1]


def test_fetch_feature_collection_retries_on_urlerror(monkeypatch):
    provider = VWorldGISBuildingProvider(
        api_key="abc123",
        page_size=1000,
        max_pages=1,
        retry_count=1,
        retry_sleep_seconds=0.0,
    )
    bounds = Bounds(126.0, 37.0, 126.1, 37.1)
    calls = {"count": 0}

    def fake_urlopen(url: str, timeout: int):
        calls["count"] += 1
        if calls["count"] == 1:
            raise URLError("temporary failure")
        return _FakeHTTPResponse({"type": "FeatureCollection", "features": [_feature("A")]})

    monkeypatch.setattr("src.data_sources.vworld.urlopen", fake_urlopen)

    merged = provider.fetch_feature_collection(bounds=bounds, crs="EPSG:4326")

    assert calls["count"] == 2
    assert len(merged["features"]) == 1


def test_fetch_feature_collection_raises_on_non_retryable_http_error(monkeypatch):
    provider = VWorldGISBuildingProvider(
        api_key="abc123",
        retry_count=3,
        retry_sleep_seconds=0.0,
    )
    bounds = Bounds(126.0, 37.0, 126.1, 37.1)
    calls = {"count": 0}

    def fake_urlopen(url: str, timeout: int):
        calls["count"] += 1
        raise HTTPError(url=url, code=400, msg="bad request", hdrs=None, fp=io.BytesIO(b"{}"))

    monkeypatch.setattr("src.data_sources.vworld.urlopen", fake_urlopen)

    with pytest.raises(RuntimeError, match="HTTP 400"):
        provider.fetch_feature_collection(bounds=bounds, crs="EPSG:4326")

    assert calls["count"] == 1
