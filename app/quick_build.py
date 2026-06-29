from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any

import geopandas as gpd
from shapely.geometry import box

from app.field_inspection import inspect_building_fields
from scripts.auto_build import auto_build
from src.data_sources import Bounds, VWorldGISBuildingProvider, fetch_buildings_geojson


ALLOWED_BUILDING_SUFFIXES = {".geojson", ".json", ".gpkg"}
ALLOWED_DEM_SUFFIXES = {".tif", ".tiff"}


def create_area_from_center(
    *,
    latitude: float,
    longitude: float,
    width_m: float,
    height_m: float,
    output_path: Path,
) -> dict[str, Any]:
    if not -90 <= latitude <= 90:
        raise ValueError("Latitude must be between -90 and 90 degrees.")
    if not -180 <= longitude <= 180:
        raise ValueError("Longitude must be between -180 and 180 degrees.")
    if not 10 <= width_m <= 5000 or not 10 <= height_m <= 5000:
        raise ValueError("Area width and height must each be between 10 m and 5,000 m.")

    latitude_delta = height_m / 111_320.0 / 2.0
    longitude_scale = max(math.cos(math.radians(latitude)), 0.01)
    longitude_delta = width_m / (111_320.0 * longitude_scale) / 2.0
    bounds = (
        longitude - longitude_delta,
        latitude - latitude_delta,
        longitude + longitude_delta,
        latitude + latitude_delta,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    gdf = gpd.GeoDataFrame({"name": [output_path.stem]}, geometry=[box(*bounds)], crs="EPSG:4326")
    gdf.to_file(output_path, driver="GeoJSON")
    return {
        "path": str(output_path.resolve()),
        "bounds": [float(value) for value in bounds],
        "area_km2": float(gdf.to_crs("EPSG:5179").geometry.area.iloc[0] / 1_000_000.0),
    }


def save_uploaded_file(*, name: str, data: bytes, directory: Path, kind: str) -> Path:
    safe_name = Path(name).name
    if not safe_name or safe_name in {".", ".."}:
        raise ValueError("Uploaded file has an invalid name.")
    allowed = ALLOWED_DEM_SUFFIXES if kind == "dem" else ALLOWED_BUILDING_SUFFIXES
    if Path(safe_name).suffix.lower() not in allowed:
        supported = ", ".join(sorted(allowed))
        raise ValueError(f"Unsupported {kind} file. Supported extensions: {supported}")
    if not data:
        raise ValueError(f"Uploaded {kind} file is empty.")
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / safe_name
    destination.write_bytes(data)
    return destination.resolve()


def fetch_vworld_buildings(
    *,
    area_path: Path,
    api_key: str,
    data_name: str,
    output_path: Path,
    cache_dir: Path = Path(".cache/data_sources"),
) -> dict[str, Any]:
    if not api_key.strip():
        raise ValueError("VWorld API key is required.")
    if not data_name.strip():
        raise ValueError("VWorld GIS building data ID is required.")
    area = gpd.read_file(area_path)
    if area.empty:
        raise ValueError("Selected area is empty.")
    if area.crs is None:
        area = area.set_crs("EPSG:4326")
    area = area.to_crs("EPSG:4326")
    min_x, min_y, max_x, max_y = area.total_bounds
    provider = VWorldGISBuildingProvider(api_key=api_key.strip(), data_name=data_name.strip())
    return fetch_buildings_geojson(
        provider=provider,
        bounds=Bounds(float(min_x), float(min_y), float(max_x), float(max_y)),
        crs="EPSG:4326",
        out_path=output_path,
        cache_dir=cache_dir,
    )


def build_quick_model(
    *,
    area_path: Path,
    dem_path: Path,
    buildings_path: Path,
    output_name: str,
    work_dir: Path,
    terrain_resolution: float = 10.0,
    export_formats: tuple[str, ...] = ("stl", "glb"),
    preview: bool = True,
) -> dict[str, Any]:
    safe_output_name = sanitize_output_name(output_name)
    registry_path = work_dir / "dataset.json"
    registry = create_quick_registry(
        area_path=area_path,
        dem_path=dem_path,
        buildings_path=buildings_path,
        registry_path=registry_path,
    )
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")
    return auto_build(
        area_path=area_path,
        registry_path=registry_path,
        dataset_name="quick-build",
        area_crs="EPSG:4326",
        output_dir=Path("output"),
        output_name=safe_output_name,
        terrain_resolution=terrain_resolution,
        terrain_boundary_mode="polygon",
        export_formats=export_formats,
        preview=preview,
        interpolate_nodata=True,
        max_area_km2=25.0,
        dry_run=False,
    )


def create_quick_registry(
    *,
    area_path: Path,
    dem_path: Path,
    buildings_path: Path,
    registry_path: Path,
) -> dict[str, Any]:
    area = gpd.read_file(area_path)
    if area.crs is None:
        area = area.set_crs("EPSG:4326")
    target_area = area.to_crs("EPSG:5179")
    inspection = inspect_building_fields(buildings_path)
    if inspection.error:
        raise ValueError(f"Could not inspect building data: {inspection.error}")
    base_dir = registry_path.resolve().parent
    return {
        "datasets": [
            {
                "name": "quick-build",
                "area": _relative_or_absolute(base_dir, area_path),
                "dem": _relative_or_absolute(base_dir, dem_path),
                "buildings": _relative_or_absolute(base_dir, buildings_path),
                "target_crs": "EPSG:5179",
                "area_crs": "EPSG:4326",
                "height_fields": list(inspection.suggested_height_fields),
                "floor_fields": list(inspection.suggested_floor_fields),
                "building_base_mode": "representative",
                "coverage_bounds": [float(value) for value in target_area.total_bounds],
                "source_date": "local-session",
                "license": "user-provided; verify before redistribution",
                "source_url": "local:quick-build",
            }
        ]
    }


def sanitize_output_name(value: str) -> str:
    sanitized = re.sub(r"[^\w-]+", "_", value.strip(), flags=re.UNICODE).strip("_")
    return sanitized[:80] or "korean_map_model"


def _relative_or_absolute(base_dir: Path, value: Path) -> str:
    try:
        return value.resolve().relative_to(base_dir).as_posix()
    except ValueError:
        return str(value.resolve())
