import argparse
import json
from pathlib import Path
from typing import Iterable


SUPPORTED_EXTENSIONS = {".stl", ".obj", ".glb", ".gltf"}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import KoreanMapSTLmaker outputs into Blender. Run through blender --python."
    )
    parser.add_argument("inputs", nargs="+", type=Path, help="Model file(s) or *_summary.json file(s).")
    parser.add_argument("--clear-scene", action="store_true", help="Clear the current scene before importing.")
    parser.add_argument("--set-metric-units", action="store_true", help="Set Blender scene units to metric.")
    parser.add_argument("--save", type=Path, help="Optional .blend path to save after import.")
    return parser.parse_args(argv)


def model_paths_from_inputs(inputs: Iterable[Path]) -> list[Path]:
    paths: list[Path] = []
    for path in inputs:
        if path.suffix.lower() == ".json":
            paths.extend(model_paths_from_summary(path))
        elif path.suffix.lower() in SUPPORTED_EXTENSIONS:
            paths.append(path)
        else:
            raise ValueError(f"Unsupported input extension for {path}. Expected model file or *_summary.json.")
    return _dedupe_paths(paths)


def model_paths_from_summary(summary_path: Path) -> list[Path]:
    summary = json.loads(summary_path.read_text(encoding="utf-8-sig"))
    outputs = summary.get("outputs")
    if not isinstance(outputs, dict):
        raise ValueError(f"{summary_path} does not contain an outputs object.")
    base_dir = summary_path.parent
    paths = []
    for value in outputs.values():
        if not isinstance(value, str) or not value.strip():
            continue
        path = Path(value)
        if not path.is_absolute():
            path = base_dir / path
        if path.suffix.lower() in SUPPORTED_EXTENSIONS:
            paths.append(path)
    if not paths:
        raise ValueError(f"{summary_path} does not list supported model outputs.")
    return paths


def import_models(paths: list[Path], *, clear_scene: bool, set_metric_units: bool, save_path: Path | None) -> None:
    try:
        import bpy
    except ModuleNotFoundError as error:
        raise RuntimeError("This script must be run inside Blender with: blender --python scripts/blender_import.py -- ...") from error

    if clear_scene:
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.object.delete()
    if set_metric_units:
        bpy.context.scene.unit_settings.system = "METRIC"
        bpy.context.scene.unit_settings.scale_length = 1.0

    for path in paths:
        _import_one(bpy, path)

    if save_path is not None:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(save_path))


def _import_one(bpy, path: Path) -> None:
    resolved = path.resolve()
    if not resolved.exists():
        raise FileNotFoundError(resolved)
    extension = resolved.suffix.lower()
    if extension == ".stl":
        bpy.ops.import_mesh.stl(filepath=str(resolved))
    elif extension == ".obj":
        if hasattr(bpy.ops.wm, "obj_import"):
            bpy.ops.wm.obj_import(filepath=str(resolved))
        else:
            bpy.ops.import_scene.obj(filepath=str(resolved))
    elif extension in {".glb", ".gltf"}:
        bpy.ops.import_scene.gltf(filepath=str(resolved))
    else:
        raise ValueError(f"Unsupported model file: {resolved}")


def _dedupe_paths(paths: list[Path]) -> list[Path]:
    seen = set()
    deduped = []
    for path in paths:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(path)
    return deduped


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    paths = model_paths_from_inputs(args.inputs)
    import_models(
        paths,
        clear_scene=args.clear_scene,
        set_metric_units=args.set_metric_units,
        save_path=args.save,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
