from __future__ import annotations

from pathlib import Path


def data_prep_defaults() -> dict[str, str]:
    return {
        "area_path": "data/sample/area.geojson",
        "area_crs": "",
        "env_file": ".env",
        "buildings_out": "data/buildings/buildings.geojson",
        "dem_source": "",
        "dem_out": "data/dem/imported_dem.tif",
        "dem_target_crs": "",
        "inspect_buildings": "data/buildings/buildings.geojson",
        "inspect_dem": "data/dem/imported_dem.tif",
    }


def build_fetch_buildings_command(
    *,
    area_path: str,
    buildings_out: str,
    env_file: str | None = None,
    area_crs: str | None = None,
) -> str:
    args = [
        python_in_venv(),
        "scripts/fetch_buildings.py",
        "--area",
        area_path,
        "--out",
        buildings_out,
        "--validate-area",
        area_path,
    ]
    if area_crs:
        args.extend(["--area-crs", area_crs])
    if env_file:
        args.extend(["--env-file", env_file])
    return join_powershell_args(args)


def build_import_dem_command(
    *,
    source_path: str,
    dem_out: str,
    area_path: str | None = None,
    area_crs: str | None = None,
    target_crs: str | None = None,
    reproject: bool = False,
) -> str:
    args = [
        python_in_venv(),
        "scripts/import_dem.py",
        "--source",
        source_path,
        "--out",
        dem_out,
    ]
    if target_crs:
        args.extend(["--target-crs", target_crs])
    if reproject:
        args.append("--reproject")
    if area_path:
        args.extend(["--validate-area", area_path])
    if area_crs:
        args.extend(["--validate-area-crs", area_crs])
    return join_powershell_args(args)


def build_inspect_data_command(
    *,
    area_path: str,
    buildings_path: str | None = None,
    dem_path: str | None = None,
    area_crs: str | None = None,
    building_crs: str | None = None,
) -> str:
    args = [
        python_in_venv(),
        "scripts/inspect_data.py",
        "--area",
        area_path,
    ]
    if area_crs:
        args.extend(["--area-crs", area_crs])
    if buildings_path:
        args.extend(["--buildings", buildings_path])
    if building_crs:
        args.extend(["--building-crs", building_crs])
    if dem_path:
        args.extend(["--dem", dem_path])
    return join_powershell_args(args)


def python_in_venv() -> str:
    return ".venv/Scripts/python.exe"


def join_powershell_args(args: list[str]) -> str:
    return " ".join(_quote_for_powershell(arg) for arg in args if str(arg).strip())


def _quote_for_powershell(value: str) -> str:
    escaped = value.replace("'", "''")
    return f"'{escaped}'"
