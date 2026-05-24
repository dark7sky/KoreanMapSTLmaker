import argparse
import json
from pathlib import Path
from typing import Any


DATASET_PATH_FIELDS = ("area", "dem", "buildings")
OPTIONAL_DATASET_FIELDS = (
    "target_crs",
    "area_crs",
    "building_crs",
    "height_fields",
    "floor_fields",
    "building_base_mode",
    "coverage_bounds",
    "source_date",
    "license",
    "source_url",
    "notes",
)
BUILDING_BASE_MODES = ("representative", "min", "mean")


def main() -> None:
    parser = argparse.ArgumentParser(description="List local datasets from datasets.json.")
    parser.add_argument(
        "--registry",
        type=Path,
        default=Path("datasets.json"),
        help="Path to the JSON dataset registry. Defaults to datasets.json.",
    )
    args = parser.parse_args()

    try:
        summary = summarize_registry(args.registry)
    except ValueError as error:
        parser.error(str(error))

    print(json.dumps(summary, indent=2, ensure_ascii=False))


def summarize_registry(registry_path: Path) -> dict[str, Any]:
    registry_path = registry_path.resolve()
    if not registry_path.exists():
        return {
            "registry": str(registry_path),
            "exists": False,
            "dataset_count": 0,
            "datasets": [],
        }

    registry = load_registry(registry_path)
    datasets = []
    for dataset in registry["datasets"]:
        paths = {
            field: str((registry_path.parent / dataset[field]).resolve())
            for field in DATASET_PATH_FIELDS
        }
        missing_paths = [
            field
            for field, path in paths.items()
            if not Path(path).exists()
        ]
        summary_entry = {
            "name": dataset["name"],
            "paths": paths,
            "missing_paths": missing_paths,
        }
        metadata = {
            field: dataset[field]
            for field in OPTIONAL_DATASET_FIELDS
            if field in dataset
        }
        if metadata:
            summary_entry["metadata"] = metadata
        datasets.append(summary_entry)

    return {
        "registry": str(registry_path),
        "exists": True,
        "dataset_count": len(datasets),
        "datasets": datasets,
    }


def load_registry(registry_path: Path) -> dict[str, Any]:
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as error:
        raise ValueError(f"{registry_path} is not valid JSON: {error.msg}") from error

    validate_registry(registry, registry_path)
    return registry


def validate_registry(registry: Any, registry_path: Path) -> None:
    if not isinstance(registry, dict):
        raise ValueError(f"{registry_path} must contain a JSON object")

    datasets = registry.get("datasets")
    if not isinstance(datasets, list):
        raise ValueError(f"{registry_path} must contain a 'datasets' list")

    names: set[str] = set()
    for index, dataset in enumerate(datasets):
        label = f"datasets[{index}]"
        if not isinstance(dataset, dict):
            raise ValueError(f"{label} must be an object")

        name = dataset.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"{label}.name must be a non-empty string")
        if name in names:
            raise ValueError(f"{label}.name duplicates {name!r}")
        names.add(name)

        for field in DATASET_PATH_FIELDS:
            value = dataset.get(field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{label}.{field} must be a non-empty string path")

        for field in ("target_crs", "area_crs", "building_crs", "notes"):
            if field in dataset:
                value = dataset[field]
                if not isinstance(value, str) or not value.strip():
                    raise ValueError(f"{label}.{field} must be a non-empty string")

        if "building_base_mode" in dataset:
            value = dataset["building_base_mode"]
            if value not in BUILDING_BASE_MODES:
                raise ValueError(f"{label}.building_base_mode must be one of: {', '.join(BUILDING_BASE_MODES)}")

        for field in ("height_fields", "floor_fields"):
            if field in dataset:
                value = dataset[field]
                if not isinstance(value, list) or not value:
                    raise ValueError(f"{label}.{field} must be a non-empty list of strings")
                for item in value:
                    if not isinstance(item, str) or not item.strip():
                        raise ValueError(f"{label}.{field} must be a non-empty list of strings")

        if "coverage_bounds" in dataset:
            bounds = dataset["coverage_bounds"]
            if not isinstance(bounds, list) or len(bounds) != 4:
                raise ValueError(f"{label}.coverage_bounds must be a list of 4 numeric values [minx, miny, maxx, maxy]")
            if not all(_is_number(value) for value in bounds):
                raise ValueError(f"{label}.coverage_bounds must be a list of 4 numeric values [minx, miny, maxx, maxy]")

        for field in ("source_date", "license", "source_url"):
            if field in dataset:
                value = dataset[field]
                if not isinstance(value, str) or not value.strip():
                    raise ValueError(f"{label}.{field} must be a non-empty string")


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


if __name__ == "__main__":
    main()
