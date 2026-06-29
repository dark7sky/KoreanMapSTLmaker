from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import geopandas as gpd

from .base import Bounds, BuildingProvider
from ..field_suggestions import suggest_fields


def fetch_buildings_geojson(
    provider: BuildingProvider,
    bounds: Bounds,
    crs: str,
    out_path: Path,
    cache_dir: Path | None,
    fixture_response: dict[str, Any] | None = None,
) -> dict[str, Any]:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    provider_identity = str(getattr(provider, "cache_identity", provider.name))
    cache_key = build_cache_key(provider_identity, bounds, crs)
    cache_path = None if cache_dir is None else cache_dir / f"{cache_key}.json"
    source = "network"

    if fixture_response is not None:
        response = fixture_response
        source = "fixture"
    elif cache_path is not None and cache_path.exists():
        response = json.loads(cache_path.read_text(encoding="utf-8"))
        source = "cache"
    else:
        response = provider.fetch_feature_collection(bounds=bounds, crs=crs)
        if cache_path is not None:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(json.dumps(response, ensure_ascii=False, indent=2), encoding="utf-8")

    geojson = extract_feature_collection(response)
    gdf = save_feature_collection_as_geojson(geojson=geojson, out_path=out_path, crs=crs)
    non_geometry_fields = [str(column) for column in gdf.columns if str(column) != "geometry"]
    suggested_height_fields = suggest_fields(non_geometry_fields, kind="height")
    suggested_floor_fields = suggest_fields(non_geometry_fields, kind="floor")
    metadata_path = write_source_metadata(
        out_path=out_path,
        provider_name=provider.name,
        crs=crs,
        bounds=bounds,
        cache_key=cache_key,
        source=source,
        request_url=redact_request_url(provider.build_request_url(bounds=bounds, crs=crs)),
        feature_count=int(len(gdf)),
        suggested_height_fields=suggested_height_fields,
        suggested_floor_fields=suggested_floor_fields,
    )
    return {
        "output_path": str(out_path),
        "metadata_path": str(metadata_path),
        "feature_count": int(len(gdf)),
        "source": source,
        "cache_key": cache_key,
        "suggested_height_fields": list(suggested_height_fields),
        "suggested_floor_fields": list(suggested_floor_fields),
    }


def save_feature_collection_as_geojson(geojson: dict[str, Any], out_path: Path, crs: str) -> gpd.GeoDataFrame:
    gdf = gpd.GeoDataFrame.from_features(geojson["features"])
    if gdf.crs is None:
        gdf = gdf.set_crs(crs)
    gdf.to_file(out_path, driver="GeoJSON")
    return gdf


def extract_feature_collection(response: dict[str, Any]) -> dict[str, Any]:
    if response.get("type") == "FeatureCollection" and isinstance(response.get("features"), list):
        return response
    candidate = response.get("response")
    if isinstance(candidate, dict):
        result = candidate.get("result")
        if isinstance(result, dict) and result.get("type") == "FeatureCollection":
            return result
    raise ValueError("Response does not include a valid FeatureCollection.")


def build_cache_key(provider_name: str, bounds: Bounds, crs: str) -> str:
    rounded = tuple(round(value, 8) for value in bounds.as_tuple())
    raw = f"{provider_name}|{crs}|{rounded[0]}|{rounded[1]}|{rounded[2]}|{rounded[3]}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def redact_request_url(request_url: str) -> str:
    parts = urlsplit(request_url)
    query = [
        (name, "***" if name.lower() in {"key", "api_key", "apikey"} else value)
        for name, value in parse_qsl(parts.query, keep_blank_values=True)
    ]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def write_source_metadata(
    out_path: Path,
    provider_name: str,
    crs: str,
    bounds: Bounds,
    cache_key: str,
    source: str,
    request_url: str,
    feature_count: int,
    suggested_height_fields: tuple[str, ...],
    suggested_floor_fields: tuple[str, ...],
) -> Path:
    metadata_path = out_path.with_name(f"{out_path.name}.source.json")
    payload = {
        "provider": provider_name,
        "crs": crs,
        "bounds": list(bounds.as_tuple()),
        "cache_key": cache_key,
        "source": source,
        "request_url": request_url,
        "feature_count": feature_count,
        "suggested_height_fields": list(suggested_height_fields),
        "suggested_floor_fields": list(suggested_floor_fields),
        "fetched_at": datetime.now(UTC).isoformat(),
    }
    metadata_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return metadata_path
