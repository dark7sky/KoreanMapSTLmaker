from dataclasses import dataclass
from typing import Mapping, Optional


HEIGHT_FIELDS = ("HEIGHT", "height", "Height", "BLD_HEIGHT", "HEIGHT_M", "BULD_HGT")
FLOOR_FIELDS = ("GRND_FLR", "ground_flo", "ground_flr", "GROUND_FLR", "FLOORS", "FLOOR_CNT")


@dataclass(frozen=True)
class HeightResult:
    value: float
    source: str


def choose_building_height(
    attrs: Mapping[str, object],
    default_floor_height: float,
    default_building_height: float,
    height_fields: Optional[tuple[str, ...]] = None,
    floor_fields: Optional[tuple[str, ...]] = None,
    min_height: float = 1.0,
    max_height: float = 300.0,
) -> HeightResult:
    height = _first_positive_number(attrs, _merge_fields(height_fields, HEIGHT_FIELDS))
    if height is not None:
        return HeightResult(_clamp(height, min_height, max_height), "HEIGHT")

    floors = _first_positive_number(attrs, _merge_fields(floor_fields, FLOOR_FIELDS))
    if floors is not None:
        return HeightResult(_clamp(floors * default_floor_height, min_height, max_height), "floor_fallback")

    return HeightResult(_clamp(default_building_height, min_height, max_height), "default")


def _first_positive_number(attrs: Mapping[str, object], fields: tuple[str, ...]) -> Optional[float]:
    for field in fields:
        if field not in attrs:
            continue
        value = _to_float(attrs[field])
        if value is not None and value > 0:
            return value
    return None


def _merge_fields(primary: Optional[tuple[str, ...]], fallback: tuple[str, ...]) -> tuple[str, ...]:
    merged: list[str] = []
    for field in (primary or ()) + fallback:
        if field and field not in merged:
            merged.append(field)
    return tuple(merged)


def _to_float(value: object) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))
