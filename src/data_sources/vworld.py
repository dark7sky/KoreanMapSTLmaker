from __future__ import annotations

import json
import time
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from .base import Bounds


@dataclass
class VWorldGISBuildingProvider:
    api_key: str | None
    base_url: str = "https://api.vworld.kr/req/data"
    data_name: str = ""
    page_size: int = 1000
    max_pages: int = 10
    retry_count: int = 1
    retry_sleep_seconds: float = 0.0
    name: str = "vworld-gis-building"

    @property
    def cache_identity(self) -> str:
        return f"{self.name}:{self.data_name.strip()}"

    def build_request_url(self, bounds: Bounds, crs: str, page: int = 1, page_size: int | None = None) -> str:
        if not self.data_name.strip():
            raise ValueError(
                "VWorld GIS building data ID is missing. Pass --data-name or set VWORLD_BUILDING_DATA_NAME."
            )
        size = self.page_size if page_size is None else page_size
        params = {
            "service": "data",
            "request": "GetFeature",
            "data": self.data_name,
            "key": self.api_key or "",
            "geomFilter": f"BBOX({bounds.as_vworld_bbox()})",
            "srsName": crs,
            "size": size,
            "page": page,
            "format": "json",
        }
        return f"{self.base_url}?{urlencode(params)}"

    def fetch_feature_collection(self, bounds: Bounds, crs: str) -> dict:
        if not self.api_key:
            raise ValueError(
                "VWORLD_API_KEY is missing. Set the environment variable, or pass --fixture-response for offline tests."
            )
        if not self.data_name.strip():
            raise ValueError(
                "VWorld GIS building data ID is missing. Pass --data-name or set VWORLD_BUILDING_DATA_NAME."
            )
        aggregated_features: list[dict] = []
        for page in range(1, max(self.max_pages, 1) + 1):
            request_url = self.build_request_url(bounds=bounds, crs=crs, page=page)
            payload = self._fetch_json_with_retry(request_url)
            page_collection = self._extract_feature_collection(payload)
            page_features = page_collection.get("features", [])
            if not isinstance(page_features, list):
                raise ValueError("VWorld FeatureCollection `features` must be a list.")
            if not page_features:
                break
            aggregated_features.extend(page_features)

            if len(page_features) < self.page_size:
                break
            number_matched = page_collection.get("numberMatched")
            if isinstance(number_matched, int) and number_matched <= len(aggregated_features):
                break

        return {"type": "FeatureCollection", "features": aggregated_features}

    def _fetch_json_with_retry(self, request_url: str) -> dict:
        attempts = max(self.retry_count, 0) + 1
        last_error: Exception | None = None
        for attempt in range(attempts):
            try:
                with urlopen(request_url, timeout=30) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                if not isinstance(payload, dict):
                    raise ValueError("VWorld response was not a JSON object.")
                return payload
            except HTTPError as error:
                last_error = error
                if not self._is_retryable_http_status(error.code) or attempt == attempts - 1:
                    raise RuntimeError(f"VWorld request failed with HTTP {error.code}. URL: {request_url}") from error
            except URLError as error:
                last_error = error
                if attempt == attempts - 1:
                    raise RuntimeError(f"VWorld request failed: {error.reason}") from error

            if self.retry_sleep_seconds > 0:
                time.sleep(self.retry_sleep_seconds)

        # Defensive fallback for type checkers: loop returns or raises earlier.
        raise RuntimeError(f"VWorld request failed after retries. URL: {request_url}") from last_error

    @staticmethod
    def _is_retryable_http_status(status_code: int) -> bool:
        return status_code in {408, 429, 500, 502, 503, 504}

    @staticmethod
    def _extract_feature_collection(payload: dict) -> dict:
        if payload.get("type") == "FeatureCollection" and isinstance(payload.get("features"), list):
            return payload
        candidate = payload.get("response")
        if isinstance(candidate, dict):
            result = candidate.get("result")
            if isinstance(result, dict) and result.get("type") == "FeatureCollection":
                return result
        raise ValueError("Response does not include a valid FeatureCollection.")
