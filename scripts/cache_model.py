import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.export import export_preview_html
from scripts.run_batch import build_model, build_options_from_job

DEFAULT_CACHE_DIR = Path(".cache") / "model_runner"
FULL_HASH_LIMIT_BYTES = 16 * 1024 * 1024
SAMPLE_SIZE_BYTES = 1024 * 1024


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run model generation with local output caching.")
    parser.add_argument("--job", type=Path, help="Job JSON path with fields similar to run_batch job entries.")
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR, help="Cache root directory.")
    parser.add_argument("--force", action="store_true", help="Bypass cache lookup and rebuild outputs.")
    parser.add_argument("--show-key", action="store_true", help="Print cache key and exit.")
    parser.add_argument("--area", type=Path, help="Area polygon file path.")
    parser.add_argument("--buildings", type=Path, help="Building footprints file path.")
    parser.add_argument("--dem", type=Path, help="DEM GeoTIFF path.")
    parser.add_argument("--out", type=Path, help="Output model path (typically .stl).")
    parser.add_argument("--target-crs", default="EPSG:5179")
    parser.add_argument("--terrain-resolution", type=float, default=10.0)
    parser.add_argument("--base-thickness", type=float, default=2.0)
    parser.add_argument("--default-floor-height", type=float, default=3.0)
    parser.add_argument("--default-building-height", type=float, default=6.0)
    parser.add_argument("--min-building-area", type=float, default=4.0)
    parser.add_argument("--simplify-tolerance", type=float, default=0.0)
    parser.add_argument("--model-scale", type=float, default=1.0)
    parser.add_argument("--max-area-km2", type=float, default=4.0)
    parser.add_argument("--export-format", action="append", choices=("stl", "obj", "glb", "gltf"))
    parser.add_argument("--separate", action="store_true")
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--z-scale", type=float, default=1.0)
    return parser.parse_args(argv)


def load_job(args: argparse.Namespace) -> dict[str, Any]:
    if args.job is not None:
        payload = json.loads(args.job.read_text(encoding="utf-8-sig"))
        if not isinstance(payload, dict):
            raise ValueError("Job JSON must be an object.")
        return payload
    if args.area is None or args.dem is None or args.out is None:
        raise ValueError("Provide --job or all of --area, --dem, and --out.")
    job: dict[str, Any] = {
        "area": str(args.area),
        "dem": str(args.dem),
        "out": str(args.out),
        "target_crs": args.target_crs,
        "terrain_resolution": args.terrain_resolution,
        "base_thickness": args.base_thickness,
        "default_floor_height": args.default_floor_height,
        "default_building_height": args.default_building_height,
        "min_building_area": args.min_building_area,
        "simplify_tolerance": args.simplify_tolerance,
        "model_scale": args.model_scale,
        "max_area_km2": args.max_area_km2,
        "separate": args.separate,
        "preview": args.preview,
        "z_scale": args.z_scale,
    }
    if args.buildings is not None:
        job["buildings"] = str(args.buildings)
    if args.export_format:
        job["export_format"] = args.export_format
    return job


def compute_cache_key(job: dict[str, Any], *, workspace: Path) -> str:
    payload = _job_signature(job, workspace=workspace)
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
    return digest


def run_cached_job(job: dict[str, Any], *, cache_dir: Path, force: bool = False, workspace: Path | None = None) -> dict[str, Any]:
    workspace_root = workspace or Path.cwd()
    cache_key = compute_cache_key(job, workspace=workspace_root)
    entry_dir = cache_dir / cache_key
    manifest_path = entry_dir / "manifest.json"
    options = build_options_from_job(job, 0)

    if not force and manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        restore_cached_outputs(entry_dir, manifest, options.out_path)
        hit_summary = rewrite_summary_paths(manifest["summary"], options.out_path)
        _write_summary_and_preview(hit_summary, options.out_path)
        return {"status": "hit", "cache_key": cache_key, "cache_entry": str(entry_dir), "summary": hit_summary}

    summary = build_model(options)
    cache_dir.mkdir(parents=True, exist_ok=True)
    save_manifest = store_cache_entry(entry_dir, cache_key, job, summary, workspace=workspace_root)
    return {"status": "miss", "cache_key": cache_key, "cache_entry": str(entry_dir), "summary": save_manifest["summary"]}


def store_cache_entry(
    entry_dir: Path,
    cache_key: str,
    job: dict[str, Any],
    summary: dict[str, Any],
    *,
    workspace: Path,
) -> dict[str, Any]:
    artifacts_dir = entry_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    outputs = dict(summary.get("outputs") or {})
    mapping: dict[str, str] = {}
    used_names: set[str] = set()
    for label, source in _all_artifact_sources(summary).items():
        source_path = Path(source)
        if not source_path.exists():
            continue
        target_name = _unique_name(source_path.name, used_names)
        shutil.copy2(source_path, artifacts_dir / target_name)
        mapping[label] = target_name
    manifest = {
        "cache_key": cache_key,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "job_signature": _job_signature(job, workspace=workspace),
        "summary": summary,
        "outputs": outputs,
        "artifacts": mapping,
    }
    entry_dir.mkdir(parents=True, exist_ok=True)
    (entry_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def restore_cached_outputs(entry_dir: Path, manifest: dict[str, Any], out_path: Path) -> None:
    artifacts_dir = entry_dir / "artifacts"
    targets = expected_outputs_from_summary(manifest["summary"], out_path)
    for label, target_path in targets.items():
        artifact_name = manifest["artifacts"].get(label)
        if artifact_name is None:
            continue
        source = artifacts_dir / artifact_name
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target_path)


def expected_outputs_from_summary(summary: dict[str, Any], out_path: Path) -> dict[str, Path]:
    targets: dict[str, Path] = {}
    formats = tuple(summary.get("export_formats") or ["stl"])
    if "stl" in formats:
        targets["output_stl"] = out_path
    if "obj" in formats:
        targets["output_obj"] = out_path.with_suffix(".obj")
    if "glb" in formats:
        targets["output_glb"] = out_path.with_suffix(".glb")
    if "gltf" in formats:
        targets["output_gltf"] = out_path.with_suffix(".gltf")
    if "terrain_stl" in (summary.get("outputs") or {}):
        targets["output_terrain_stl"] = out_path.with_name(f"{out_path.stem}_terrain.stl")
    if "buildings_stl" in (summary.get("outputs") or {}):
        targets["output_buildings_stl"] = out_path.with_name(f"{out_path.stem}_buildings.stl")
    targets["summary_json"] = out_path.with_name(f"{out_path.stem}_summary.json")
    if "preview" in summary:
        targets["preview_html"] = out_path.with_name(f"{out_path.stem}_preview.html")
    return targets


def rewrite_summary_paths(summary: dict[str, Any], out_path: Path) -> dict[str, Any]:
    rewritten = json.loads(json.dumps(summary))
    outputs: dict[str, str] = {}
    if "stl" in rewritten.get("export_formats", ["stl"]):
        outputs["stl"] = str(out_path)
    if "obj" in rewritten.get("export_formats", []):
        outputs["obj"] = str(out_path.with_suffix(".obj"))
    if "glb" in rewritten.get("export_formats", []):
        outputs["glb"] = str(out_path.with_suffix(".glb"))
    if "gltf" in rewritten.get("export_formats", []):
        outputs["gltf"] = str(out_path.with_suffix(".gltf"))
    if "terrain_stl" in (rewritten.get("outputs") or {}):
        outputs["terrain_stl"] = str(out_path.with_name(f"{out_path.stem}_terrain.stl"))
    if "buildings_stl" in (rewritten.get("outputs") or {}):
        outputs["buildings_stl"] = str(out_path.with_name(f"{out_path.stem}_buildings.stl"))
    rewritten["outputs"] = outputs
    first_format = rewritten.get("export_formats", ["stl"])[0]
    rewritten["output"] = outputs.get(first_format, str(out_path))
    rewritten["summary"] = str(out_path.with_name(f"{out_path.stem}_summary.json"))
    if "preview" in rewritten:
        rewritten["preview"] = str(out_path.with_name(f"{out_path.stem}_preview.html"))
    options = dict(rewritten.get("options") or {})
    options["out"] = str(out_path)
    rewritten["options"] = options
    return rewritten


def _write_summary_and_preview(summary: dict[str, Any], out_path: Path) -> None:
    summary_path = out_path.with_name(f"{out_path.stem}_summary.json")
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    if "preview" in summary and out_path.exists():
        export_preview_html(out_path, summary)


def _all_artifact_sources(summary: dict[str, Any]) -> dict[str, str]:
    artifacts: dict[str, str] = {}
    outputs = summary.get("outputs") or {}
    if "stl" in outputs:
        artifacts["output_stl"] = outputs["stl"]
    if "obj" in outputs:
        artifacts["output_obj"] = outputs["obj"]
    if "glb" in outputs:
        artifacts["output_glb"] = outputs["glb"]
    if "gltf" in outputs:
        artifacts["output_gltf"] = outputs["gltf"]
    if "terrain_stl" in outputs:
        artifacts["output_terrain_stl"] = outputs["terrain_stl"]
    if "buildings_stl" in outputs:
        artifacts["output_buildings_stl"] = outputs["buildings_stl"]
    if "summary" in summary:
        artifacts["summary_json"] = summary["summary"]
    if "preview" in summary:
        artifacts["preview_html"] = summary["preview"]
    return artifacts


def _job_signature(job: dict[str, Any], *, workspace: Path) -> dict[str, Any]:
    normalized = json.loads(json.dumps(job))
    normalized.pop("out", None)
    file_fields = ("area", "buildings", "dem")
    file_fingerprints: dict[str, Any] = {}
    for key in file_fields:
        value = normalized.get(key)
        if isinstance(value, str) and value.strip():
            file_fingerprints[key] = _fingerprint_file(_resolve_job_path(value, workspace))
    normalized["file_fingerprints"] = file_fingerprints
    return normalized


def _resolve_job_path(raw_path: str, workspace: Path) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path.resolve()
    return (workspace / path).resolve()


def _fingerprint_file(path: Path) -> dict[str, Any]:
    stat = path.stat()
    digest, mode = _hash_file(path)
    return {
        "path": str(path),
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "hash": digest,
        "hash_mode": mode,
    }


def _hash_file(path: Path) -> tuple[str, str]:
    size = path.stat().st_size
    hasher = hashlib.sha256()
    if size <= FULL_HASH_LIMIT_BYTES:
        with path.open("rb") as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                hasher.update(chunk)
        return hasher.hexdigest(), "full"
    with path.open("rb") as file:
        head = file.read(SAMPLE_SIZE_BYTES)
        if size > SAMPLE_SIZE_BYTES:
            file.seek(max(size - SAMPLE_SIZE_BYTES, 0))
        tail = file.read(SAMPLE_SIZE_BYTES)
    hasher.update(head)
    hasher.update(tail)
    hasher.update(str(size).encode("ascii"))
    return hasher.hexdigest(), "sampled"


def _unique_name(name: str, used: set[str]) -> str:
    if name not in used:
        used.add(name)
        return name
    stem = Path(name).stem
    suffix = Path(name).suffix
    index = 2
    while True:
        candidate = f"{stem}_{index}{suffix}"
        if candidate not in used:
            used.add(candidate)
            return candidate
        index += 1


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    job = load_job(args)
    cache_key = compute_cache_key(job, workspace=Path.cwd())
    if args.show_key:
        print(cache_key)
        return 0
    result = run_cached_job(job, cache_dir=args.cache_dir, force=args.force, workspace=Path.cwd())
    print(f"Cache: {result['status']} ({result['cache_key']})")
    print(f"Output: {result['summary']['output']}")
    print(f"Summary: {result['summary']['summary']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
