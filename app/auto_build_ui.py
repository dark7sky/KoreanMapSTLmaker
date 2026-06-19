import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from scripts.auto_build import auto_build, format_text_report


@dataclass
class AutoBuildRunResult:
    ok: bool
    elapsed_seconds: float
    report: dict | None = None
    text_report: str | None = None
    error: str | None = None


def default_auto_build_values() -> dict[str, object]:
    return {
        "area_path": "data/sample/area.geojson",
        "registry_path": "datasets.sample.json",
        "dataset_name": "",
        "area_crs": "",
        "target_crs": "EPSG:5179",
        "output_dir": "output",
        "output_name": "sample_block",
        "terrain_resolution": 10.0,
        "terrain_boundary_mode": "polygon",
        "export_formats": ["stl"],
        "preview": True,
        "dry_run": True,
        "interpolate_nodata": False,
        "z_scale": 1.0,
        "model_scale": 1.0,
        "base_plate_thickness": 0.0,
        "base_plate_margin": 0.0,
        "max_area_km2": 4.0,
    }


def run_auto_build_from_values(
    values: dict[str, object],
    *,
    auto_build_fn: Callable[..., dict] = auto_build,
) -> AutoBuildRunResult:
    started = time.perf_counter()
    try:
        report = auto_build_fn(
            area_path=Path(str(values["area_path"]).strip()),
            registry_path=Path(str(values["registry_path"]).strip()),
            dataset_name=_optional_string(values.get("dataset_name")),
            target_crs=str(values.get("target_crs", "EPSG:5179")).strip() or "EPSG:5179",
            area_crs=_optional_string(values.get("area_crs")),
            output_dir=Path(str(values.get("output_dir", "output")).strip() or "output"),
            output_name=_optional_string(values.get("output_name")),
            terrain_resolution=float(values.get("terrain_resolution", 10.0)),
            terrain_boundary_mode=str(values.get("terrain_boundary_mode", "polygon")).strip() or "polygon",
            export_formats=_export_formats(values.get("export_formats")),
            preview=bool(values.get("preview", False)),
            interpolate_nodata=bool(values.get("interpolate_nodata", False)),
            z_scale=float(values.get("z_scale", 1.0)),
            model_scale=float(values.get("model_scale", 1.0)),
            base_plate_thickness=float(values.get("base_plate_thickness", 0.0)),
            base_plate_margin=float(values.get("base_plate_margin", 0.0)),
            max_area_km2=float(values.get("max_area_km2", 4.0)),
            dry_run=bool(values.get("dry_run", False)),
        )
    except Exception as exc:  # pragma: no cover - exercised by tests with fake callable
        return AutoBuildRunResult(ok=False, elapsed_seconds=time.perf_counter() - started, error=str(exc))
    return AutoBuildRunResult(
        ok=report.get("status") in {"validated", "built"},
        elapsed_seconds=time.perf_counter() - started,
        report=report,
        text_report=format_text_report(report),
        error=None if report.get("status") in {"validated", "built"} else "Auto build did not complete.",
    )


def _optional_string(raw: object) -> str | None:
    value = str(raw).strip() if raw is not None else ""
    return value or None


def _export_formats(raw: object) -> tuple[str, ...]:
    if isinstance(raw, str):
        values = [raw]
    elif raw is None:
        values = ["stl"]
    else:
        values = [str(value) for value in raw]
    normalized = tuple(dict.fromkeys(value.strip().lower() for value in values if value.strip()))
    return normalized or ("stl",)
