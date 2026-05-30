from pathlib import Path
from typing import Any, Mapping

from src.pipeline import BuildOptions


def default_form_values() -> dict[str, Any]:
    return {
        "area_path": "data/sample/area.geojson",
        "buildings_path": "data/sample/buildings.geojson",
        "dem_path": "data/sample/dem.tif",
        "out_path": "output/model.stl",
        "target_crs": "EPSG:5179",
        "area_crs": "",
        "building_crs": "",
        "dem_crs": "",
        "terrain_resolution": 10.0,
        "terrain_resampling": "nearest",
        "terrain_boundary_mode": "grid",
        "terrain_smoothing_iterations": 0,
        "terrain_smoothing_factor": 0.5,
        "interpolate_nodata": False,
        "base_thickness": 2.0,
        "default_floor_height": 3.0,
        "default_building_height": 6.0,
        "min_building_area": 4.0,
        "simplify_tolerance": 0.0,
        "model_scale": 1.0,
        "base_plate_thickness": 0.0,
        "base_plate_margin": 0.0,
        "max_area_km2": 4.0,
        "building_diagnostics_limit": 200,
        "separate": False,
        "preview": False,
        "height_fields": "",
        "floor_fields": "",
        "building_base_mode": "representative",
        "export_formats": ["stl"],
        "z_scale": 1.0,
    }


def to_build_options(values: Mapping[str, Any]) -> BuildOptions:
    export_formats = values.get("export_formats", ["stl"])
    dedup_formats = tuple(dict.fromkeys(str(fmt).strip() for fmt in export_formats if str(fmt).strip()))
    if not dedup_formats:
        dedup_formats = ("stl",)

    return BuildOptions(
        area_path=Path(str(values["area_path"]).strip()),
        buildings_path=_optional_path(values.get("buildings_path")),
        dem_path=Path(str(values["dem_path"]).strip()),
        out_path=Path(str(values["out_path"]).strip()),
        target_crs=str(values.get("target_crs", "EPSG:5179")).strip() or "EPSG:5179",
        area_crs=_optional_string(values.get("area_crs")),
        building_crs=_optional_string(values.get("building_crs")),
        dem_crs=_optional_string(values.get("dem_crs")),
        terrain_resolution=float(values.get("terrain_resolution", 10.0)),
        terrain_resampling=str(values.get("terrain_resampling", "nearest")).strip() or "nearest",
        terrain_boundary_mode=str(values.get("terrain_boundary_mode", "grid")).strip() or "grid",
        terrain_smoothing_iterations=int(values.get("terrain_smoothing_iterations", 0)),
        terrain_smoothing_factor=float(values.get("terrain_smoothing_factor", 0.5)),
        interpolate_nodata=bool(values.get("interpolate_nodata", False)),
        base_thickness=float(values.get("base_thickness", 2.0)),
        default_floor_height=float(values.get("default_floor_height", 3.0)),
        default_building_height=float(values.get("default_building_height", 6.0)),
        min_building_area=float(values.get("min_building_area", 4.0)),
        simplify_tolerance=float(values.get("simplify_tolerance", 0.0)),
        model_scale=float(values.get("model_scale", 1.0)),
        base_plate_thickness=float(values.get("base_plate_thickness", 0.0)),
        base_plate_margin=float(values.get("base_plate_margin", 0.0)),
        max_area_km2=float(values.get("max_area_km2", 4.0)),
        building_diagnostics_limit=int(values.get("building_diagnostics_limit", 200)),
        separate=bool(values.get("separate", False)),
        preview=bool(values.get("preview", False)),
        height_fields=_parse_fields(values.get("height_fields")),
        floor_fields=_parse_fields(values.get("floor_fields")),
        building_base_mode=str(values.get("building_base_mode", "representative")).strip() or "representative",
        export_formats=dedup_formats,
        z_scale=float(values.get("z_scale", 1.0)),
    )


def _optional_path(raw: Any) -> Path | None:
    value = str(raw).strip() if raw is not None else ""
    return Path(value) if value else None


def _optional_string(raw: Any) -> str | None:
    value = str(raw).strip() if raw is not None else ""
    return value or None


def _parse_fields(raw: Any) -> tuple[str, ...] | None:
    if raw is None:
        return None
    if isinstance(raw, str):
        fields = [part.strip() for part in raw.split(",")]
    else:
        fields = [str(part).strip() for part in raw]
    filtered = tuple(part for part in fields if part)
    return filtered or None
