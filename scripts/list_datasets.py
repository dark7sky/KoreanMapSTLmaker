import argparse
import json
from pathlib import Path
from typing import Any


DATASET_PATH_FIELDS = ("area", "dem", "buildings")


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
        datasets.append(
            {
                "name": dataset["name"],
                "paths": paths,
                "missing_paths": missing_paths,
            }
        )

    return {
        "registry": str(registry_path),
        "exists": True,
        "dataset_count": len(datasets),
        "datasets": datasets,
    }


def load_registry(registry_path: Path) -> dict[str, Any]:
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
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


if __name__ == "__main__":
    main()
