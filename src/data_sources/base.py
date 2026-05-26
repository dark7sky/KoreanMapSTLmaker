from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Bounds:
    min_x: float
    min_y: float
    max_x: float
    max_y: float

    def as_tuple(self) -> tuple[float, float, float, float]:
        return (self.min_x, self.min_y, self.max_x, self.max_y)

    def as_vworld_bbox(self) -> str:
        return f"{self.min_x},{self.min_y},{self.max_x},{self.max_y}"


class BuildingProvider(Protocol):
    name: str

    def build_request_url(self, bounds: Bounds, crs: str) -> str:
        ...

    def fetch_feature_collection(self, bounds: Bounds, crs: str) -> dict:
        ...
