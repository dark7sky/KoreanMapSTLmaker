from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.command_from_dataset import find_dataset, maybe_add_multi, maybe_add_pair, to_powershell_command
from scripts.list_datasets import load_registry
from scripts.run_batch import build_options_from_job
from scripts.select_dataset import select_datasets
from scripts.validate_real_dataset import validate_real_dataset
from src.pipeline import BuildOptions, build_model


BuildFn = Callable[[BuildOptions], dict[str, Any]]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Select the best local dataset for a drawn area, validate inputs, and build a 3D model."
    )
    parser.add_argument("--area", required=True, type=Path, help="Selected area GeoJSON/SHP/GPKG file.")
    parser.add_argument("--registry", type=Path, default=Path("datasets.json"), help="Dataset registry JSON path.")
    parser.add_argument("--dataset", help="Use a named dataset instead of overlap-based auto selection.")
    parser.add_argument("--target-crs", default="EPSG:5179", help="Modeling CRS used for selection and build.")
    parser.add_argument("--area-crs", help="Fallback CRS for the selected area when metadata is missing.")
    parser.add_argument("--output-dir", type=Path, default=Path("output"), help="Directory for generated output.")
    parser.add_argument("--output-name", help="Output stem. Defaults to the selected dataset name.")
    parser.add_argument("--terrain-resolution", type=float, default=10.0, help="Terrain sampling resolution in meters.")
    parser.add_argument(
        "--terrain-boundary-mode",
        choices=("grid", "polygon"),
        default="polygon",
        help="Use polygon for tighter output around the selected area.",
    )
    parser.add_argument("--export-format", action="append", default=None, help="Export format: stl, obj, glb, gltf.")
    parser.add_argument("--preview", action="store_true", help="Generate preview HTML.")
    parser.add_argument("--interpolate-nodata", action="store_true", help="Fill small DEM nodata holes.")
    parser.add_argument("--z-scale", type=float, default=1.0, help="Terrain vertical exaggeration.")
    parser.add_argument("--model-scale", type=float, default=1.0, help="Final mesh scale.")
    parser.add_argument("--base-plate-thickness", type=float, default=0.0, help="Optional base plate thickness.")
    parser.add_argument("--base-plate-margin", type=float, default=0.0, help="Optional base plate margin.")
    parser.add_argument("--max-area-km2", type=float, default=4.0, help="Safety limit for selected area.")
    parser.add_argument("--dry-run", action="store_true", help="Select and validate, but do not generate the model.")
    parser.add_argument("--force", action="store_true", help="Build even when validation has FAIL checks.")
    parser.add_argument("--format", choices=("text", "json"), default="text", help="Terminal output format.")
    parser.add_argument("--summary-out", type=Path, help="Write auto-build report JSON.")
    return parser.parse_args(argv)


def auto_build(
    *,
    area_path: Path,
    registry_path: Path,
    dataset_name: str | None = None,
    target_crs: str = "EPSG:5179",
    area_crs: str | None = None,
    output_dir: Path = Path("output"),
    output_name: str | None = None,
    terrain_resolution: float = 10.0,
    terrain_boundary_mode: str = "polygon",
    export_formats: tuple[str, ...] = ("stl",),
    preview: bool = False,
    interpolate_nodata: bool = False,
    z_scale: float = 1.0,
    model_scale: float = 1.0,
    base_plate_thickness: float = 0.0,
    base_plate_margin: float = 0.0,
    max_area_km2: float = 4.0,
    dry_run: bool = False,
    force: bool = False,
    build_fn: BuildFn = build_model,
) -> dict[str, Any]:
    registry = load_registry(registry_path)
    dataset, selection = _choose_dataset(
        registry=registry,
        registry_path=registry_path,
        area_path=area_path,
        dataset_name=dataset_name,
        target_crs=target_crs,
        area_crs=area_crs,
    )
    job = build_job_from_dataset(
        registry_path=registry_path,
        dataset=dataset,
        area_path=area_path,
        target_crs=target_crs,
        area_crs=area_crs,
        output_dir=output_dir,
        output_name=output_name,
        terrain_resolution=terrain_resolution,
        terrain_boundary_mode=terrain_boundary_mode,
        export_formats=export_formats,
        preview=preview,
        interpolate_nodata=interpolate_nodata,
        z_scale=z_scale,
        model_scale=model_scale,
        base_plate_thickness=base_plate_thickness,
        base_plate_margin=base_plate_margin,
        max_area_km2=max_area_km2,
    )
    validation = validate_real_dataset(
        area_path=Path(job["area"]),
        buildings_path=Path(job["buildings"]),
        dem_path=Path(job["dem"]),
        area_crs=job.get("area_crs"),
        building_crs=job.get("building_crs"),
        target_crs=job["target_crs"],
    )
    report: dict[str, Any] = {
        "status": "validated" if dry_run else "pending",
        "dry_run": dry_run,
        "dataset": {
            "name": dataset["name"],
            "metadata": _dataset_metadata(dataset),
        },
        "selection": selection,
        "job": job,
        "validation": validation,
        "command": build_powershell_command(job),
        "build": None,
    }
    if not validation["ok"] and not force:
        report["status"] = "validation_failed"
        return report
    if dry_run:
        return report

    options = build_options_from_job(job, 0)
    summary = build_fn(options)
    report["status"] = "built"
    report["build"] = summary
    return report


def build_job_from_dataset(
    *,
    registry_path: Path,
    dataset: dict[str, Any],
    area_path: Path,
    target_crs: str,
    area_crs: str | None,
    output_dir: Path,
    output_name: str | None,
    terrain_resolution: float,
    terrain_boundary_mode: str,
    export_formats: tuple[str, ...],
    preview: bool,
    interpolate_nodata: bool,
    z_scale: float,
    model_scale: float,
    base_plate_thickness: float,
    base_plate_margin: float,
    max_area_km2: float,
) -> dict[str, Any]:
    base_dir = registry_path.resolve().parent
    stem = output_name or dataset["name"]
    job: dict[str, Any] = {
        "name": stem,
        "area": str(area_path),
        "buildings": str((base_dir / dataset["buildings"]).resolve()),
        "dem": str((base_dir / dataset["dem"]).resolve()),
        "out": str((output_dir / f"{stem}.stl").resolve()),
        "target_crs": dataset.get("target_crs", target_crs),
        "terrain_resolution": terrain_resolution,
        "terrain_boundary_mode": terrain_boundary_mode,
        "export_format": list(export_formats),
        "preview": preview,
        "interpolate_nodata": interpolate_nodata,
        "z_scale": z_scale,
        "model_scale": model_scale,
        "base_plate_thickness": base_plate_thickness,
        "base_plate_margin": base_plate_margin,
        "max_area_km2": max_area_km2,
        "building_diagnostics_limit": 200,
    }
    selected_area_crs = area_crs or dataset.get("area_crs")
    if selected_area_crs:
        job["area_crs"] = selected_area_crs
    for dataset_key, job_key in (
        ("building_crs", "building_crs"),
        ("dem_crs", "dem_crs"),
        ("building_base_mode", "building_base_mode"),
        ("height_fields", "height_field"),
        ("floor_fields", "floor_field"),
    ):
        if dataset_key in dataset:
            job[job_key] = dataset[dataset_key]
    return job


def build_powershell_command(job: dict[str, Any]) -> str:
    parts = [
        ".\\.venv\\Scripts\\python.exe",
        "make_model.py",
        "--area",
        str(job["area"]),
        "--buildings",
        str(job["buildings"]),
        "--dem",
        str(job["dem"]),
        "--out",
        str(job["out"]),
    ]
    for flag, key in (
        ("--target-crs", "target_crs"),
        ("--area-crs", "area_crs"),
        ("--building-crs", "building_crs"),
        ("--dem-crs", "dem_crs"),
        ("--building-base-mode", "building_base_mode"),
        ("--terrain-resolution", "terrain_resolution"),
        ("--terrain-boundary-mode", "terrain_boundary_mode"),
        ("--z-scale", "z_scale"),
        ("--model-scale", "model_scale"),
        ("--base-plate-thickness", "base_plate_thickness"),
        ("--base-plate-margin", "base_plate_margin"),
        ("--max-area-km2", "max_area_km2"),
    ):
        maybe_add_pair(parts, flag, job.get(key))
    maybe_add_multi(parts, "--height-field", job.get("height_field"))
    maybe_add_multi(parts, "--floor-field", job.get("floor_field"))
    maybe_add_multi(parts, "--export-format", job.get("export_format"))
    if job.get("preview"):
        parts.append("--preview")
    if job.get("interpolate_nodata"):
        parts.append("--interpolate-nodata")
    return to_powershell_command([str(part) for part in parts])


def format_text_report(report: dict[str, Any]) -> str:
    lines = [
        f"Status: {report['status']}",
        f"Dataset: {report['dataset']['name']}",
        f"Dry run: {report['dry_run']}",
    ]
    selection = report.get("selection", {})
    if selection.get("mode") == "overlap":
        match = selection.get("best_match", {})
        ratio = float(match.get("area_overlap_ratio", 0.0)) * 100.0
        lines.append(f"Area coverage: {ratio:.1f}%")
    validation = report.get("validation", {})
    lines.append(f"Validation: {'PASS' if validation.get('ok') else 'FAIL'}")
    errors = validation.get("errors") or []
    if errors:
        lines.append("Validation errors:")
        for error in errors[:5]:
            lines.append(f"  - {error}")
        if len(errors) > 5:
            lines.append(f"  - ... {len(errors) - 5} more")

    build = report.get("build")
    if isinstance(build, dict):
        outputs = build.get("outputs")
        if isinstance(outputs, dict) and outputs:
            lines.append("Outputs:")
            for label, path in outputs.items():
                lines.append(f"  - {label}: {path}")
        elif build.get("output"):
            lines.append(f"Output: {build['output']}")
        if build.get("preview"):
            lines.append(f"Preview: {build['preview']}")
        if build.get("summary"):
            lines.append(f"Model summary: {build['summary']}")
    else:
        lines.append("Build: not run")

    lines.extend(["Equivalent make_model.py command:", report["command"]])
    return "\n".join(lines)


def _choose_dataset(
    *,
    registry: dict[str, Any],
    registry_path: Path,
    area_path: Path,
    dataset_name: str | None,
    target_crs: str,
    area_crs: str | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if dataset_name:
        dataset = find_dataset(registry["datasets"], dataset_name)
        return dataset, {"mode": "named", "name": dataset_name}

    selection = select_datasets(
        registry_path=registry_path,
        area_path=area_path,
        target_crs=target_crs,
        area_crs=area_crs,
        limit=1,
    )
    if not selection["matches"]:
        raise ValueError("No registry dataset overlaps the selected area. Add coverage_bounds or pass --dataset.")
    match = selection["matches"][0]
    dataset = find_dataset(registry["datasets"], match["name"])
    return dataset, {"mode": "overlap", "best_match": match, "area": selection["area"]}


def _dataset_metadata(dataset: dict[str, Any]) -> dict[str, Any]:
    return {
        key: dataset[key]
        for key in ("target_crs", "coverage_bounds", "source_date", "license", "source_url", "notes")
        if key in dataset
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    formats = tuple(dict.fromkeys(args.export_format or ["stl"]))
    try:
        report = auto_build(
            area_path=args.area,
            registry_path=args.registry,
            dataset_name=args.dataset,
            target_crs=args.target_crs,
            area_crs=args.area_crs,
            output_dir=args.output_dir,
            output_name=args.output_name,
            terrain_resolution=args.terrain_resolution,
            terrain_boundary_mode=args.terrain_boundary_mode,
            export_formats=formats,
            preview=args.preview,
            interpolate_nodata=args.interpolate_nodata,
            z_scale=args.z_scale,
            model_scale=args.model_scale,
            base_plate_thickness=args.base_plate_thickness,
            base_plate_margin=args.base_plate_margin,
            max_area_km2=args.max_area_km2,
            dry_run=args.dry_run,
            force=args.force,
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.summary_out:
        args.summary_out.parent.mkdir(parents=True, exist_ok=True)
        args.summary_out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    if args.format == "json":
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(format_text_report(report))
    return 0 if report["status"] in {"validated", "built"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
