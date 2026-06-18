from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from rasterio.errors import RasterioIOError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data_sources.validation import validate_area_overlaps_dem


def validate_real_dem(
    *,
    dem_path: Path,
    target_crs: str = "EPSG:5179",
    area_path: Path | None = None,
    area_crs: str | None = None,
    source_name: str | None = None,
    source_date: str | None = None,
    license_name: str | None = None,
    source_url: str | None = None,
) -> dict[str, Any]:
    checks: list[dict[str, str]] = []
    errors: list[str] = []
    warnings: list[str] = []
    path = dem_path.resolve()

    if not path.exists():
        message = f"Missing DEM file: {path}"
        checks.append({"name": "dem_exists", "status": "fail", "message": message})
        return _result(
            ok=False,
            dem_path=path,
            checks=checks,
            errors=[message],
            warnings=[],
            metadata={},
            target_crs=target_crs,
            source_name=source_name,
            source_date=source_date,
            license_name=license_name,
            source_url=source_url,
        )

    checks.append({"name": "dem_exists", "status": "pass", "message": str(path)})
    suffix = path.suffix.lower()
    checks.append(
        {
            "name": "dem_geotiff_extension",
            "status": "pass" if suffix in {".tif", ".tiff"} else "warn",
            "message": f"extension={suffix or '<none>'}",
        }
    )

    metadata: dict[str, Any]
    try:
        metadata = inspect_dem_metadata(path)
    except (RasterioIOError, ValueError) as exc:
        message = f"Could not open DEM as a raster: {exc}"
        checks.append({"name": "dem_readable", "status": "fail", "message": message})
        return _result(
            ok=False,
            dem_path=path,
            checks=checks,
            errors=[message],
            warnings=[],
            metadata={},
            target_crs=target_crs,
            source_name=source_name,
            source_date=source_date,
            license_name=license_name,
            source_url=source_url,
        )

    checks.extend(_quality_checks(metadata, target_crs))
    if area_path:
        try:
            overlap = validate_area_overlaps_dem(
                area_path=area_path.resolve(),
                dem_path=path,
                target_crs=target_crs,
                area_crs=area_crs,
            )
            checks.append(
                {
                    "name": "area_dem_overlap",
                    "status": "pass" if overlap.overlaps else "fail",
                    "message": (
                        f"target_crs={overlap.target_crs}; area_bounds={overlap.area_bounds}; "
                        f"dem_bounds={overlap.source_bounds}"
                    ),
                }
            )
        except Exception as exc:  # pragma: no cover - defensive path for mixed GIS driver failures
            checks.append({"name": "area_dem_overlap", "status": "fail", "message": str(exc)})

    for check in checks:
        if check["status"] == "fail":
            errors.append(check["message"])
        elif check["status"] == "warn":
            warnings.append(check["message"])

    return _result(
        ok=not errors,
        dem_path=path,
        checks=checks,
        errors=errors,
        warnings=warnings,
        metadata=metadata,
        target_crs=target_crs,
        source_name=source_name,
        source_date=source_date,
        license_name=license_name,
        source_url=source_url,
    )


def inspect_dem_metadata(path: Path) -> dict[str, Any]:
    with rasterio.open(path) as dataset:
        if dataset.count < 1:
            raise ValueError("raster has no bands")

        band = dataset.read(1, masked=True)
        valid_values = band.compressed()
        bounds = dataset.bounds
        transform = dataset.transform
        stats = _stats(valid_values)
        total_cells = int(dataset.width * dataset.height)
        valid_cells = int(valid_values.size)

        return {
            "path": str(path),
            "driver": dataset.driver,
            "crs": None if dataset.crs is None else str(dataset.crs),
            "bounds": [float(bounds.left), float(bounds.bottom), float(bounds.right), float(bounds.top)],
            "width": int(dataset.width),
            "height": int(dataset.height),
            "count": int(dataset.count),
            "resolution": [float(abs(dataset.res[0])), float(abs(dataset.res[1]))],
            "transform": [float(value) for value in transform[:6]],
            "nodata": None if dataset.nodata is None else float(dataset.nodata),
            "dtypes": list(dataset.dtypes),
            "valid_cells": valid_cells,
            "nodata_cells": total_cells - valid_cells,
            "nodata_fraction": 0.0 if total_cells == 0 else float((total_cells - valid_cells) / total_cells),
            "elevation": stats,
        }


def _quality_checks(metadata: dict[str, Any], target_crs: str) -> list[dict[str, str]]:
    checks: list[dict[str, str]] = [
        {"name": "dem_readable", "status": "pass", "message": f"driver={metadata['driver']}"},
        {
            "name": "dem_geotiff_driver",
            "status": "pass" if metadata["driver"] == "GTiff" else "warn",
            "message": f"driver={metadata['driver']}",
        },
        {
            "name": "dem_crs_present",
            "status": "pass" if metadata["crs"] else "fail",
            "message": f"crs={metadata['crs']}",
        },
        {
            "name": "dem_target_crs",
            "status": "pass" if metadata["crs"] == target_crs else "warn",
            "message": f"dem_crs={metadata['crs']}; target_crs={target_crs}",
        },
        {
            "name": "dem_size_valid",
            "status": "pass" if metadata["width"] > 0 and metadata["height"] > 0 else "fail",
            "message": f"width={metadata['width']}, height={metadata['height']}",
        },
        {
            "name": "dem_band_count",
            "status": "pass" if metadata["count"] == 1 else "warn",
            "message": f"count={metadata['count']}",
        },
        {
            "name": "dem_resolution_positive",
            "status": "pass" if all(value > 0 for value in metadata["resolution"]) else "fail",
            "message": f"resolution={metadata['resolution']}",
        },
        {
            "name": "dem_numeric_dtype",
            "status": "pass" if all(np.dtype(dtype).kind in {"i", "u", "f"} for dtype in metadata["dtypes"]) else "fail",
            "message": f"dtypes={metadata['dtypes']}",
        },
        {
            "name": "dem_valid_elevation_samples",
            "status": "pass" if metadata["valid_cells"] > 0 else "fail",
            "message": f"valid_cells={metadata['valid_cells']}; nodata_cells={metadata['nodata_cells']}",
        },
        {
            "name": "dem_nodata_coverage",
            "status": "warn" if metadata["nodata_fraction"] > 0.25 else "pass",
            "message": f"nodata_fraction={metadata['nodata_fraction']:.4f}",
        },
    ]

    elevation = metadata["elevation"]
    finite_stats = all(
        elevation.get(key) is not None and math.isfinite(float(elevation[key])) for key in ("min", "max", "mean")
    )
    checks.append(
        {
            "name": "dem_elevation_stats",
            "status": "pass" if finite_stats else "fail",
            "message": f"min={elevation.get('min')}; max={elevation.get('max')}; mean={elevation.get('mean')}",
        }
    )
    return checks


def _stats(values: np.ndarray) -> dict[str, float | None]:
    if values.size == 0:
        return {"min": None, "max": None, "mean": None}
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return {"min": None, "max": None, "mean": None}
    return {
        "min": float(np.min(finite)),
        "max": float(np.max(finite)),
        "mean": float(np.mean(finite)),
    }


def _result(
    *,
    ok: bool,
    dem_path: Path,
    checks: list[dict[str, str]],
    errors: list[str],
    warnings: list[str],
    metadata: dict[str, Any],
    target_crs: str,
    source_name: str | None,
    source_date: str | None,
    license_name: str | None,
    source_url: str | None,
) -> dict[str, Any]:
    return {
        "ok": ok,
        "errors": errors,
        "warnings": warnings,
        "inputs": {"dem": str(dem_path)},
        "target_crs": target_crs,
        "source": {
            "name": source_name,
            "date": source_date,
            "license": license_name,
            "url": source_url,
        },
        "dem": metadata,
        "checks": checks,
        "next_steps": _next_steps(checks),
    }


def _next_steps(checks: list[dict[str, str]]) -> list[str]:
    failed = {check["name"] for check in checks if check["status"] == "fail"}
    warned = {check["name"] for check in checks if check["status"] == "warn"}
    steps: list[str] = []
    if "dem_crs_present" in failed:
        steps.append("Add or repair DEM CRS metadata before import; do not guess CRS from file name alone.")
    if "dem_target_crs" in warned:
        steps.append("Import with scripts/import_dem.py --target-crs EPSG:5179 --reproject before modeling.")
    if "area_dem_overlap" in failed:
        steps.append("Check area CRS and DEM CRS/bounds; model generation requires overlap in the target CRS.")
    if "dem_nodata_coverage" in warned:
        steps.append("Review nodata coverage and consider --interpolate-nodata only for small holes inside the area.")
    if not steps:
        steps.append("DEM is ready to import/register or use directly with make_model.py.")
    return steps


def _format_text_report(result: dict[str, Any]) -> str:
    lines = [f"REAL_DEM_VALIDATION {'PASS' if result.get('ok') else 'FAIL'}"]
    source = result.get("source", {})
    if any(source.values()):
        lines.append(
            "Source: "
            + ", ".join(f"{key}={value}" for key, value in source.items() if value not in (None, ""))
        )
    dem = result.get("dem", {})
    if dem:
        lines.append(
            f"DEM: crs={dem.get('crs')}; bounds={dem.get('bounds')}; "
            f"shape={dem.get('height')}x{dem.get('width')}; resolution={dem.get('resolution')}"
        )
        lines.append(
            f"Elevation: {dem.get('elevation')}; valid_cells={dem.get('valid_cells')}; "
            f"nodata_fraction={dem.get('nodata_fraction')}"
        )
    for check in result.get("checks", []):
        lines.append(f"[{check['status'].upper()}] {check['name']}: {check['message']}")
    lines.append("Next steps:")
    for step in result.get("next_steps", []):
        lines.append(f"- {step}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Offline metadata report and checklist for user-supplied NGII/Public Data DEM GeoTIFFs."
    )
    parser.add_argument("--dem", required=True, type=Path, help="DEM GeoTIFF path.")
    parser.add_argument("--target-crs", default="EPSG:5179", help="Expected modeling CRS.")
    parser.add_argument("--area", type=Path, help="Optional area file used to validate DEM overlap.")
    parser.add_argument("--area-crs", help="Fallback CRS when --area has no CRS metadata.")
    parser.add_argument("--source-name", help="Optional source/product name for the report.")
    parser.add_argument("--source-date", help="Optional source acquisition/publication date string.")
    parser.add_argument("--license", dest="license_name", help="Optional data license string.")
    parser.add_argument("--source-url", help="Optional source URL.")
    parser.add_argument("--format", choices=("text", "json"), default="text", help="Terminal output format.")
    parser.add_argument("--json-out", type=Path, help="Optional path to save the JSON report.")
    args = parser.parse_args()

    result = validate_real_dem(
        dem_path=args.dem,
        target_crs=args.target_crs,
        area_path=args.area,
        area_crs=args.area_crs,
        source_name=args.source_name,
        source_date=args.source_date,
        license_name=args.license_name,
        source_url=args.source_url,
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
