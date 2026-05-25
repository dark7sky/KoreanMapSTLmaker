import argparse
import json
import sys
from pathlib import Path
from typing import Any

from shapely.geometry import box

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.command_from_dataset import maybe_add_multi, maybe_add_pair, to_powershell_command
from scripts.list_datasets import load_registry
from src.io import load_area


def main() -> None:
    parser = argparse.ArgumentParser(description="Select registry datasets whose coverage overlaps an area file.")
    parser.add_argument("--area", required=True, type=Path, help="Area polygon file used for matching.")
    parser.add_argument("--registry", type=Path, default=Path("datasets.json"), help="Dataset registry JSON path.")
    parser.add_argument("--target-crs", default="EPSG:5179", help="CRS used to compare area and coverage bounds.")
    parser.add_argument("--area-crs", help="Fallback CRS when the area file has none.")
    parser.add_argument("--limit", type=int, default=5, help="Maximum matches to return.")
    parser.add_argument("--commands", action="store_true", help="Print inspect/model commands for the best match.")
    args = parser.parse_args()

    result = select_datasets(
        registry_path=args.registry,
        area_path=args.area,
        target_crs=args.target_crs,
        area_crs=args.area_crs,
        limit=args.limit,
    )
    if args.commands:
        if not result["matches"]:
            raise SystemExit("No matching datasets found.")
        print_commands_for_match(args.registry, args.area, result["matches"][0])
        return
    print(json.dumps(result, indent=2, ensure_ascii=False))


def select_datasets(
    *,
    registry_path: Path,
    area_path: Path,
    target_crs: str,
    area_crs: str | None = None,
    limit: int = 5,
) -> dict[str, Any]:
    area, area_km2 = load_area(area_path, target_crs, area_crs)
    area_bounds = [float(value) for value in area.bounds]
    area_box = box(*area_bounds)
    registry = load_registry(registry_path)
    matches = []
    skipped = []

    for dataset in registry["datasets"]:
        bounds = dataset.get("coverage_bounds")
        if bounds is None:
            skipped.append({"name": dataset["name"], "reason": "missing coverage_bounds"})
            continue
        coverage = box(*bounds)
        if not coverage.intersects(area_box):
            continue
        intersection_area = float(coverage.intersection(area_box).area)
        if intersection_area <= 0:
            continue
        coverage_area = float(coverage.area)
        area_overlap_ratio = intersection_area / float(area_box.area) if area_box.area else 0.0
        coverage_overlap_ratio = intersection_area / coverage_area if coverage_area else 0.0
        matches.append(
            {
                "name": dataset["name"],
                "coverage_bounds": [float(value) for value in bounds],
                "intersection_area": intersection_area,
                "area_overlap_ratio": area_overlap_ratio,
                "coverage_overlap_ratio": coverage_overlap_ratio,
                "metadata": _metadata(dataset),
            }
        )

    matches.sort(key=lambda item: (item["area_overlap_ratio"], item["intersection_area"]), reverse=True)
    if limit >= 0:
        matches = matches[:limit]
    return {
        "registry": str(registry_path.resolve()),
        "area": str(area_path),
        "target_crs": target_crs,
        "area_km2": area_km2,
        "area_bounds": area_bounds,
        "match_count": len(matches),
        "matches": matches,
        "skipped": skipped,
    }


def print_commands_for_match(registry_path: Path, area_path: Path, match: dict[str, Any]) -> None:
    registry = load_registry(registry_path)
    dataset = next(dataset for dataset in registry["datasets"] if dataset["name"] == match["name"])
    base_dir = registry_path.resolve().parent
    dem = str((base_dir / dataset["dem"]).resolve())
    buildings = str((base_dir / dataset["buildings"]).resolve())
    output_stl = str((Path("output") / f"{dataset['name']}.stl").resolve())

    inspect_parts = [
        ".\\.venv\\Scripts\\python.exe",
        "scripts\\inspect_data.py",
        "--area",
        str(area_path),
        "--buildings",
        buildings,
        "--dem",
        dem,
    ]
    maybe_add_pair(inspect_parts, "--area-crs", dataset.get("area_crs"))
    maybe_add_pair(inspect_parts, "--building-crs", dataset.get("building_crs"))

    make_parts = [
        ".\\.venv\\Scripts\\python.exe",
        "make_model.py",
        "--area",
        str(area_path),
        "--buildings",
        buildings,
        "--dem",
        dem,
        "--out",
        output_stl,
    ]
    maybe_add_pair(make_parts, "--target-crs", dataset.get("target_crs"))
    maybe_add_pair(make_parts, "--area-crs", dataset.get("area_crs"))
    maybe_add_pair(make_parts, "--building-crs", dataset.get("building_crs"))
    maybe_add_pair(make_parts, "--building-base-mode", dataset.get("building_base_mode"))
    maybe_add_multi(make_parts, "--height-field", dataset.get("height_fields"))
    maybe_add_multi(make_parts, "--floor-field", dataset.get("floor_fields"))

    print(to_powershell_command(inspect_parts))
    print(to_powershell_command(make_parts))


def _metadata(dataset: dict[str, Any]) -> dict[str, Any]:
    return {
        key: dataset[key]
        for key in ("target_crs", "source_date", "license", "source_url", "notes")
        if key in dataset
    }


if __name__ == "__main__":
    main()
