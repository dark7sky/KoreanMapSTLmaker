import json
import shutil
from pathlib import Path
from typing import Any

import rasterio
from rasterio.crs import CRS
from rasterio.warp import Resampling, calculate_default_transform, reproject


def inspect_dem(path: Path) -> dict[str, Any]:
    source = path.resolve()
    with rasterio.open(source) as dataset:
        if dataset.crs is None:
            raise ValueError(f"DEM has no CRS: {source}")
        return {
            "path": str(source),
            "crs": str(dataset.crs),
            "bounds": [
                float(dataset.bounds.left),
                float(dataset.bounds.bottom),
                float(dataset.bounds.right),
                float(dataset.bounds.top),
            ],
            "width": int(dataset.width),
            "height": int(dataset.height),
            "count": int(dataset.count),
            "resolution": [float(abs(dataset.res[0])), float(abs(dataset.res[1]))],
            "nodata": None if dataset.nodata is None else float(dataset.nodata),
            "dtypes": [str(value) for value in dataset.dtypes],
        }


def import_dem(
    *,
    source_path: Path,
    output_path: Path,
    target_crs: str | None = None,
    reproject_if_needed: bool = False,
) -> dict[str, Any]:
    source = source_path.resolve()
    output = output_path.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(source) as dataset:
        if dataset.crs is None:
            raise ValueError(f"DEM has no CRS: {source}")
        source_crs = dataset.crs
        selected_target = _parse_target_crs(target_crs) if target_crs else source_crs
        if source_crs == selected_target:
            shutil.copy2(source, output)
        else:
            if not reproject_if_needed:
                raise ValueError(
                    "Source CRS does not match --target-crs. "
                    "Re-run with --reproject to allow reprojection."
                )
            _reproject_to_target(dataset, output, selected_target)

    metadata = inspect_dem(output)
    metadata["source_path"] = str(source)
    metadata["output_path"] = str(output)
    return metadata


def write_sidecar(sidecar_path: Path, payload: dict[str, Any]) -> None:
    sidecar_path.parent.mkdir(parents=True, exist_ok=True)
    sidecar_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def update_dem_registry(
    *,
    registry_path: Path,
    name: str,
    metadata: dict[str, Any],
    source_date: str | None = None,
    license_name: str | None = None,
    source_url: str | None = None,
) -> dict[str, Any]:
    target = registry_path.resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        registry = json.loads(target.read_text(encoding="utf-8-sig"))
        if not isinstance(registry, dict):
            raise ValueError(f"{target} must contain a JSON object")
    else:
        registry = {}

    dem_datasets = registry.get("dem_datasets")
    if dem_datasets is None:
        dem_datasets = []
        registry["dem_datasets"] = dem_datasets
    if not isinstance(dem_datasets, list):
        raise ValueError(f"{target}.dem_datasets must be a list when present")

    entry = {
        "name": name,
        "dem": _to_registry_relative(target.parent, Path(metadata["output_path"])),
        "crs": metadata["crs"],
        "bounds": metadata["bounds"],
        "resolution": metadata["resolution"],
        "shape": [metadata["height"], metadata["width"]],
        "nodata": metadata["nodata"],
        "dtypes": metadata["dtypes"],
        "source_path": metadata["source_path"],
    }
    if source_date:
        entry["source_date"] = source_date
    if license_name:
        entry["license"] = license_name
    if source_url:
        entry["source_url"] = source_url

    existing = next((item for item in dem_datasets if isinstance(item, dict) and item.get("name") == name), None)
    if existing is None:
        dem_datasets.append(entry)
    else:
        existing.clear()
        existing.update(entry)

    target.write_text(json.dumps(registry, indent=2, ensure_ascii=False), encoding="utf-8")
    return registry


def _to_registry_relative(base: Path, value: Path) -> str:
    try:
        return value.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return str(value.resolve())


def _parse_target_crs(value: str) -> CRS:
    parsed = CRS.from_user_input(value)
    if not parsed:
        raise ValueError(f"Invalid --target-crs value: {value}")
    return parsed


def _reproject_to_target(dataset: rasterio.DatasetReader, output_path: Path, target_crs: CRS) -> None:
    transform, width, height = calculate_default_transform(
        dataset.crs,
        target_crs,
        dataset.width,
        dataset.height,
        *dataset.bounds,
    )
    profile = dataset.profile.copy()
    profile.update(
        {
            "crs": target_crs,
            "transform": transform,
            "width": width,
            "height": height,
        }
    )
    with rasterio.open(output_path, "w", **profile) as destination:
        for index in range(1, dataset.count + 1):
            reproject(
                source=rasterio.band(dataset, index),
                destination=rasterio.band(destination, index),
                src_transform=dataset.transform,
                src_crs=dataset.crs,
                dst_transform=transform,
                dst_crs=target_crs,
                resampling=Resampling.bilinear,
                src_nodata=dataset.nodata,
                dst_nodata=dataset.nodata,
            )
