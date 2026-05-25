import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.pipeline import BuildOptions, build_model


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run multiple make_model jobs from a JSON batch file.")
    parser.add_argument(
        "--batch",
        required=True,
        type=Path,
        help='Batch JSON path with top-level {"jobs":[...]}',
    )
    parser.add_argument("--summary-out", type=Path, help="Write batch execution summary JSON to this path.")
    parser.add_argument("--retries", type=_non_negative_int, default=0, help="Retry each failed job this many times.")
    parser.add_argument("--workers", type=_positive_int, default=1, help="Number of jobs to run in parallel.")
    return parser.parse_args(argv)


def load_jobs(batch_path: Path) -> list[dict[str, Any]]:
    if not batch_path.exists():
        raise FileNotFoundError(batch_path)
    payload = json.loads(batch_path.read_text(encoding="utf-8-sig"))
    jobs = payload.get("jobs")
    if not isinstance(jobs, list):
        raise ValueError('Batch JSON must contain top-level key "jobs" as a list.')
    normalized: list[dict[str, Any]] = []
    for index, job in enumerate(jobs):
        if not isinstance(job, dict):
            raise ValueError(f"Job at index {index} must be an object.")
        normalized.append(job)
    return normalized


def _require_path(job: dict[str, Any], key: str, job_index: int) -> Path:
    value = job.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'Job {job_index}: "{key}" is required and must be a non-empty string.')
    return Path(value)


def _get_float(job: dict[str, Any], key: str, default: float) -> float:
    value = job.get(key, default)
    if isinstance(value, bool):
        raise ValueError(f'"{key}" must be numeric when provided.')
    try:
        return float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f'"{key}" must be numeric when provided.') from error


def _get_bool(job: dict[str, Any], key: str, default: bool) -> bool:
    value = job.get(key, default)
    if isinstance(value, bool):
        return value
    raise ValueError(f'"{key}" must be a boolean when provided.')


def _get_string(job: dict[str, Any], key: str, default: str | None) -> str | None:
    value = job.get(key, default)
    if value is None:
        return None
    return str(value)


def _get_tuple_of_strings(job: dict[str, Any], key: str) -> tuple[str, ...]:
    value = job.get(key)
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ValueError(f'"{key}" must be a list when provided.')
    if not all(isinstance(item, str) and item.strip() for item in value):
        raise ValueError(f'"{key}" must be a list of non-empty strings when provided.')
    return tuple(value)


def _get_export_formats(job: dict[str, Any]) -> tuple[str, ...]:
    values = job.get("export_format", ["stl"])
    if isinstance(values, str):
        values = [values]
    if not isinstance(values, list) or not values:
        raise ValueError('"export_format" must be a non-empty list or a string.')
    if not all(isinstance(value, str) and value.strip() for value in values):
        raise ValueError('"export_format" must contain non-empty strings.')
    normalized = tuple(dict.fromkeys(value.lower() for value in values))
    invalid = [value for value in normalized if value not in {"stl", "obj", "glb"}]
    if invalid:
        raise ValueError(f"Unsupported export format(s): {', '.join(invalid)}")
    return normalized


def build_options_from_job(job: dict[str, Any], job_index: int) -> BuildOptions:
    return BuildOptions(
        area_path=_require_path(job, "area", job_index),
        buildings_path=Path(job["buildings"]) if isinstance(job.get("buildings"), str) else None,
        dem_path=_require_path(job, "dem", job_index),
        out_path=_require_path(job, "out", job_index),
        target_crs=_get_string(job, "target_crs", "EPSG:5179") or "EPSG:5179",
        area_crs=_get_string(job, "area_crs", None),
        building_crs=_get_string(job, "building_crs", None),
        terrain_resolution=_get_float(job, "terrain_resolution", 10.0),
        base_thickness=_get_float(job, "base_thickness", 2.0),
        default_floor_height=_get_float(job, "default_floor_height", 3.0),
        default_building_height=_get_float(job, "default_building_height", 6.0),
        min_building_area=_get_float(job, "min_building_area", 4.0),
        simplify_tolerance=_get_float(job, "simplify_tolerance", 0.0),
        model_scale=_get_float(job, "model_scale", 1.0),
        base_plate_thickness=_get_float(job, "base_plate_thickness", 0.0),
        base_plate_margin=_get_float(job, "base_plate_margin", 0.0),
        max_area_km2=_get_float(job, "max_area_km2", 4.0),
        separate=_get_bool(job, "separate", False),
        preview=_get_bool(job, "preview", False),
        height_fields=_get_tuple_of_strings(job, "height_field"),
        floor_fields=_get_tuple_of_strings(job, "floor_field"),
        building_base_mode=_get_string(job, "building_base_mode", "representative") or "representative",
        export_formats=_get_export_formats(job),
        z_scale=_get_float(job, "z_scale", 1.0),
    )


def run_jobs(jobs: list[dict[str, Any]], *, retries: int = 0, workers: int = 1) -> dict[str, Any]:
    if workers < 1:
        raise ValueError("workers must be 1 or greater")
    if workers == 1:
        results = [_run_one_job(index, job, retries) for index, job in enumerate(jobs)]
    else:
        results_by_index: dict[int, dict[str, Any]] = {}
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(_run_one_job, index, job, retries): index
                for index, job in enumerate(jobs)
            }
            for future in as_completed(futures):
                index = futures[future]
                results_by_index[index] = future.result()
        results = [results_by_index[index] for index in range(len(jobs))]
    failure_count = sum(1 for result in results if result["status"] == "failed")
    return {
        "job_count": len(jobs),
        "success_count": len(jobs) - failure_count,
        "failure_count": failure_count,
        "workers": workers,
        "jobs": results,
    }


def _run_one_job(index: int, job: dict[str, Any], retries: int) -> dict[str, Any]:
    job_name = str(job.get("name") or f"job_{index + 1}")
    record: dict[str, Any] = {"index": index, "name": job_name}
    errors: list[str] = []
    for attempt in range(retries + 1):
        try:
            options = build_options_from_job(job, index)
            summary = build_model(options)
            record["status"] = "ok"
            record["attempts"] = attempt + 1
            record["output"] = summary.get("output")
            record["summary"] = summary.get("summary")
            break
        except Exception as exc:  # pragma: no cover - exercised in tests via monkeypatch
            errors.append(str(exc))
    if "status" not in record:
        record["status"] = "failed"
        record["attempts"] = retries + 1
        record["error"] = errors[-1]
        record["errors"] = errors
    return record


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    jobs = load_jobs(args.batch)
    if args.summary_out is not None:
        _check_summary_out_does_not_collide(args.summary_out, jobs)
    batch_summary = run_jobs(jobs, retries=args.retries, workers=args.workers)
    if args.summary_out is not None:
        args.summary_out.parent.mkdir(parents=True, exist_ok=True)
        args.summary_out.write_text(json.dumps(batch_summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return 1 if batch_summary["failure_count"] > 0 else 0


def _check_summary_out_does_not_collide(summary_out: Path, jobs: list[dict[str, Any]]) -> None:
    summary_path = summary_out.resolve()
    for index, job in enumerate(jobs):
        out_value = job.get("out")
        if not isinstance(out_value, str) or not out_value.strip():
            continue
        model_summary_path = Path(out_value).with_name(f"{Path(out_value).stem}_summary.json").resolve()
        if model_summary_path == summary_path:
            raise ValueError(
                f'--summary-out collides with model summary for job {index}: "{model_summary_path}"'
            )


def _non_negative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be 0 or greater")
    return parsed


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be 1 or greater")
    return parsed


if __name__ == "__main__":
    raise SystemExit(main())
