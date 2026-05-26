from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from .base import Bounds


@dataclass
class VWorldGISBuildingProvider:
    api_key: str | None
    base_url: str = "https://api.vworld.kr/req/data"
    data_name: str = "LT_C_UQ111"
    page_size: int = 1000
    name: str = "vworld-gis-building"

    def build_request_url(self, bounds: Bounds, crs: str) -> str:
        params = {
            "service": "data",
            "request": "GetFeature",
            "data": self.data_name,
            "key": self.api_key or "",
            "geomFilter": f"BBOX({bounds.as_vworld_bbox()})",
            "srsName": crs,
            "size": self.page_size,
            "page": 1,
            "format": "json",
        }
        return f"{self.base_url}?{urlencode(params)}"

    def fetch_feature_collection(self, bounds: Bounds, crs: str) -> dict:
        if not self.api_key:
            raise ValueError(
                "VWORLD_API_KEY is missing. Set the environment variable, or pass --fixture-response for offline tests."
            )
        request_url = self.build_request_url(bounds=bounds, crs=crs)
        try:
            with urlopen(request_url, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            raise RuntimeError(f"VWorld request failed with HTTP {error.code}. URL: {request_url}") from error
        except URLError as error:
            raise RuntimeError(f"VWorld request failed: {error.reason}") from error
        if not isinstance(payload, dict):
            raise ValueError("VWorld response was not a JSON object.")
        return payload
