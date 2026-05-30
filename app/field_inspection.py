from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import geopandas as gpd

from src.field_suggestions import suggest_fields


@dataclass(frozen=True)
class FieldInspectionResult:
    fields: tuple[str, ...]
    suggested_height_fields: tuple[str, ...]
    suggested_floor_fields: tuple[str, ...]
    error: str | None = None


def inspect_building_fields(path: str | Path, top_n: int = 5) -> FieldInspectionResult:
    target = Path(path)
    try:
        gdf = gpd.read_file(target)
    except Exception as exc:
        return FieldInspectionResult(fields=(), suggested_height_fields=(), suggested_floor_fields=(), error=str(exc))

    fields = tuple(str(column) for column in gdf.columns if str(column) != "geometry")
    return FieldInspectionResult(
        fields=fields,
        suggested_height_fields=suggest_fields(fields, kind="height", top_n=top_n),
        suggested_floor_fields=suggest_fields(fields, kind="floor", top_n=top_n),
    )
