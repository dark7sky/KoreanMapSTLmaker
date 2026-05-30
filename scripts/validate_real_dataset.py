from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.inspect_data import inspect_raster, inspect_vector
from src.data_sources.validation import validate_area_overlaps_dem, validate_area_overlaps_vector
from src.field_suggestions import suggest_fields


def validate_real_dataset(
    *,
    area_path: Path,
    buildings_path: Path,
    dem_path: Path,
    area_crs: str | None = None,
    building_crs: str | None = None,
    target_crs: str = "EPSG:5179",
) -> dict[str, Any]:
    checks: list[dict[str, str]] = []
    errors: list[str] = []

    inputs = {
        "area": _resolve_input(area_path),
        "buildings": _resolve_input(buildings_path),
        "dem": _resolve_input(dem_path),
    }
    for label, path in inputs.items():
        if path.exists():
            checks.append({"name": f"{label}_exists", "status": "pass", "message": str(path)})
        else:
            checks.append({"name": f"{label}_exists", "status": "fail", "message": f"Missing file: {path}"})
            errors.append(f"{label} file does not exist: {path}")

    if errors:
        return {
            "ok": False,
            "errors": errors,
            "inputs": {key: str(value) for key, value in inputs.items()},
            "checks": checks,
        }

    area_info = inspect_vector(inputs["area"], area_crs)
    building_info = inspect_vector(inputs["buildings"], building_crs)
    dem_info = inspect_raster(inputs["dem"])

    _append_vector_quality_checks(checks, "area", area_info)
    _append_vector_quality_checks(checks, "buildings", building_info)
    _append_dem_quality_checks(checks, dem_info)

    suggested_height_fields = suggest_fields(building_info.get("fields", []), "height")
    suggested_floor_fields = suggest_fields(building_info.get("fields", []), "floor")
    checks.append(
        {
            "name": "buildings_height_field_candidates",
            "status": "pass" if suggested_height_fields else "warn",
            "message": ", ".join(suggested_height_fields) if suggested_height_fields else "No likely height fields found.",
        }
    )
    checks.append(
        {
            "name": "buildings_floor_field_candidates",
            "status": "pass" if suggested_floor_fields else "warn",
            "message": ", ".join(suggested_floor_fields) if suggested_floor_fields else "No likely floor fields found.",
        }
    )

    try:
        vector_overlap = validate_area_overlaps_vector(
            area_path=inputs["area"],
            vector_path=inputs["buildings"],
            target_crs=target_crs,
            area_crs=area_crs,
            vector_crs=building_crs,
            source_label="building",
        )
        checks.append(
            {
                "name": "area_buildings_overlap",
                "status": "pass" if vector_overlap.overlaps else "fail",
                "message": (
                    f"target_crs={vector_overlap.target_crs}; area_bounds={vector_overlap.area_bounds}; "
                    f"building_bounds={vector_overlap.source_bounds}"
                ),
            }
        )
    except Exception as exc:  # pragma: no cover - defensive error path
        checks.append({"name": "area_buildings_overlap", "status": "fail", "message": str(exc)})

    try:
        dem_overlap = validate_area_overlaps_dem(
            area_path=inputs["area"],
            dem_path=inputs["dem"],
            target_crs=target_crs,
            area_crs=area_crs,
        )
        checks.append(
            {
                "name": "area_dem_overlap",
                "status": "pass" if dem_overlap.overlaps else "fail",
                "message": (
                    f"target_crs={dem_overlap.target_crs}; area_bounds={dem_overlap.area_bounds}; "
                    f"dem_bounds={dem_overlap.source_bounds}"
                ),
            }
        )
    except Exception as exc:  # pragma: no cover - defensive error path
        checks.append({"name": "area_dem_overlap", "status": "fail", "message": str(exc)})

    failed = [item for item in checks if item["status"] == "fail"]
    warns = [item for item in checks if item["status"] == "warn"]
    return {
        "ok": not failed,
        "errors": [item["message"] for item in failed],
        "warnings": [item["message"] for item in warns],
        "inputs": {key: str(value) for key, value in inputs.items()},
        "target_crs": target_crs,
        "area": area_info,
        "buildings": building_info,
        "dem": dem_info,
        "suggested_fields": {
            "height": list(suggested_height_fields),
            "floor": list(suggested_floor_fields),
        },
        "checks": checks,
    }


def _resolve_input(path: Path) -> Path:
    return path.resolve()


def _append_vector_quality_checks(checks: list[dict[str, str]], label: str, vector_info: dict[str, Any]) -> None:
    feature_count = int(vector_info.get("feature_count", 0))
    checks.append(
        {
            "name": f"{label}_feature_count",
            "status": "pass" if feature_count > 0 else "fail",
            "message": f"feature_count={feature_count}",
        }
    )
    crs = vector_info.get("crs")
    checks.append(
        {
            "name": f"{label}_crs_present",
            "status": "pass" if crs else "fail",
            "message": f"crs={crs}",
        }
    )
    geometry_types = set(vector_info.get("geometry_types", []))
    expected_polygons = {"Polygon", "MultiPolygon"}
    checks.append(
        {
            "name": f"{label}_geometry_type",
            "status": "pass" if geometry_types & expected_polygons else "warn",
            "message": f"geometry_types={sorted(geometry_types)}",
        }
    )


def _append_dem_quality_checks(checks: list[dict[str, str]], dem_info: dict[str, Any]) -> None:
    dem_crs = dem_info.get("crs")
    checks.append({"name": "dem_crs_present", "status": "pass" if dem_crs else "fail", "message": f"crs={dem_crs}"})

    width = int(dem_info.get("width", 0))
    height = int(dem_info.get("height", 0))
    checks.append(
        {
            "name": "dem_size_valid",
            "status": "pass" if width > 0 and height > 0 else "fail",
            "message": f"width={width}, height={height}",
        }
    )

    count = int(dem_info.get("count", 0))
    checks.append({"name": "dem_band_count", "status": "pass" if count >= 1 else "fail", "message": f"count={count}"})


def _format_text_report(result: dict[str, Any]) -> str:
    lines = [f"REAL_DATA_VALIDATION {'PASS' if result.get('ok') else 'FAIL'}"]
    for check in result.get("checks", []):
        lines.append(f"[{check['status'].upper()}] {check['name']}: {check['message']}")
    if result.get("warnings"):
        lines.append("Warnings:")
        for warning in result["warnings"]:
            lines.append(f"- {warning}")
    if result.get("errors"):
        lines.append("Errors:")
        for error in result["errors"]:
            lines.append(f"- {error}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Offline validation checklist for real area/building/DEM files before model generation."
    )
    parser.add_argument("--area", required=True, type=Path, help="Area vector file.")
    parser.add_argument("--buildings", required=True, type=Path, help="Building vector file.")
    parser.add_argument("--dem", required=True, type=Path, help="DEM raster file.")
    parser.add_argument("--area-crs", help="Fallback area CRS when area CRS metadata is missing.")
    parser.add_argument("--building-crs", help="Fallback building CRS when building CRS metadata is missing.")
    parser.add_argument("--target-crs", default="EPSG:5179", help="Target CRS used for overlap checks.")
    parser.add_argument("--format", choices=("text", "json"), default="text", help="Terminal output format.")
    parser.add_argument("--json-out", type=Path, help="Optional path to save the JSON report.")
    args = parser.parse_args()

    result = validate_real_dataset(
        area_path=args.area,
        buildings_path=args.buildings,
        dem_path=args.dem,
        area_crs=args.area_crs,
        building_crs=args.building_crs,
        target_crs=args.target_crs,
    )

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    if args.format == "json":
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(_format_text_report(result))

    if not result.get("ok", False):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
