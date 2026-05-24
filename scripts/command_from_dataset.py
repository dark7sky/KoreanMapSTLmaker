import argparse
from pathlib import Path

try:
    from scripts.list_datasets import load_registry
except ModuleNotFoundError:
    from list_datasets import load_registry


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Print PowerShell command templates for a dataset in datasets.json."
    )
    parser.add_argument("dataset", help="Dataset name from datasets.json")
    parser.add_argument(
        "--registry",
        type=Path,
        default=Path("datasets.json"),
        help="Path to the JSON dataset registry. Defaults to datasets.json.",
    )
    args = parser.parse_args()

    inspect_command, make_model_command = build_commands(args.registry, args.dataset)
    print(inspect_command)
    print(make_model_command)


def build_commands(registry_path: Path, dataset_name: str) -> tuple[str, str]:
    registry = load_registry(registry_path)
    dataset = find_dataset(registry["datasets"], dataset_name)
    base_dir = registry_path.resolve().parent

    area = resolve_dataset_path(base_dir, dataset["area"])
    dem = resolve_dataset_path(base_dir, dataset["dem"])
    buildings = resolve_dataset_path(base_dir, dataset["buildings"])

    inspect_parts = [
        ".\\.venv\\Scripts\\python.exe",
        "scripts\\inspect_data.py",
        "--area",
        area,
        "--buildings",
        buildings,
        "--dem",
        dem,
    ]
    maybe_add_pair(inspect_parts, "--area-crs", dataset.get("area_crs"))
    maybe_add_pair(inspect_parts, "--building-crs", dataset.get("building_crs"))

    output_stl = str((Path("output") / f"{dataset_name}.stl").resolve())
    make_parts = [
        ".\\.venv\\Scripts\\python.exe",
        "make_model.py",
        "--area",
        area,
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

    return to_powershell_command(inspect_parts), to_powershell_command(make_parts)


def find_dataset(datasets: list[dict], dataset_name: str) -> dict:
    for dataset in datasets:
        if dataset["name"] == dataset_name:
            return dataset
    raise ValueError(f"Dataset {dataset_name!r} was not found in the registry")


def resolve_dataset_path(base_dir: Path, value: str) -> str:
    return str((base_dir / value).resolve())


def maybe_add_pair(parts: list[str], flag: str, value: object) -> None:
    if isinstance(value, str) and value.strip():
        parts.extend([flag, value])


def maybe_add_multi(parts: list[str], flag: str, values: object) -> None:
    if not isinstance(values, list):
        return
    for value in values:
        parts.extend([flag, str(value)])


def to_powershell_command(parts: list[str]) -> str:
    return " ".join(powershell_quote(part) for part in parts)


def powershell_quote(value: str) -> str:
    if any(char.isspace() for char in value):
        return "'" + value.replace("'", "''") + "'"
    return value


if __name__ == "__main__":
    main()
