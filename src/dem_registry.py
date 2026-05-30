import json
from pathlib import Path
from typing import Any

from rasterio.warp import transform_bounds
from shapely.geometry import box


def load_dem_registry(registry_path: Path) -> dict[str, Any]:
    target = registry_path.resolve()
    if not target.exists():
        return {"dem_datasets": []}

    payload = json.loads(target.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{target} must contain a JSON object")

    dem_datasets = payload.get("dem_datasets")
    if dem_datasets is None:
        payload["dem_datasets"] = []
        return payload
    if not isinstance(dem_datasets, list):
        raise ValueError(f"{target}.dem_datasets must be a list when present")

    for index, item in enumerate(dem_datasets):
        if not isinstance(item, dict):
            raise ValueError(f"dem_datasets[{index}] must be an object")

    return payload


def find_dem_tiles(
    *,
    registry_path: Path,
    query_bounds: list[float],
    query_crs: str,
    limit: int = 10,
) -> dict[str, Any]:
    registry = load_dem_registry(registry_path)
    query_box = box(*query_bounds)
    matches = []
    skipped = []

    for index, dataset in enumerate(registry["dem_datasets"]):
        label = dataset.get("name", f"dem_datasets[{index}]")
        bounds = dataset.get("bounds")
        crs = dataset.get("crs")
        if not _valid_bounds(bounds):
            skipped.append({"name": label, "reason": "missing or invalid bounds"})
            continue
        if not isinstance(crs, str) or not crs.strip():
            skipped.append({"name": label, "reason": "missing or invalid crs"})
            continue

        try:
            mapped_bounds = [float(value) for value in transform_bounds(query_crs, crs, *query_bounds)]
        except Exception:
            skipped.append({"name": label, "reason": "failed to transform bounds"})
            continue

        query_in_dataset_crs = box(*mapped_bounds)
        coverage = box(*[float(value) for value in bounds])
        if not coverage.intersects(query_in_dataset_crs):
            continue

        intersection_area = float(coverage.intersection(query_in_dataset_crs).area)
        if intersection_area <= 0:
            continue

        query_area = float(query_in_dataset_crs.area)
        coverage_area = float(coverage.area)
        matches.append(
            {
                "name": label,
                "dem": dataset.get("dem"),
                "crs": crs,
                "bounds": [float(value) for value in bounds],
                "intersection_area": intersection_area,
                "query_overlap_ratio": intersection_area / query_area if query_area else 0.0,
                "coverage_overlap_ratio": intersection_area / coverage_area if coverage_area else 0.0,
            }
        )

    matches.sort(key=lambda item: (item["query_overlap_ratio"], item["intersection_area"]), reverse=True)
    if limit >= 0:
        matches = matches[:limit]

    return {
        "registry": str(registry_path.resolve()),
        "query_crs": query_crs,
        "query_bounds": [float(value) for value in query_box.bounds],
        "match_count": len(matches),
        "matches": matches,
        "skipped": skipped,
    }


def _valid_bounds(value: Any) -> bool:
    if not isinstance(value, list) or len(value) != 4:
        return False
    for item in value:
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            return False
    return True
