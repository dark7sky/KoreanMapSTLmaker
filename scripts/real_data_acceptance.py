from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


SAMPLE_MARKERS = ("data/sample", "datasets.sample.json", "project fixture", "local:data/sample")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify real-data validation reports and write acceptance evidence.")
    parser.add_argument("--dataset-report", required=True, type=Path, help="JSON from scripts/validate_real_dataset.py.")
    parser.add_argument("--dem-report", required=True, type=Path, help="JSON from scripts/validate_real_dem.py.")
    parser.add_argument("--out", type=Path, default=Path("output/real_data_acceptance.json"))
    parser.add_argument("--allow-sample", action="store_true", help="Allow committed sample fixture paths for testing only.")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args(argv)


def validate_acceptance(
    *,
    dataset_report_path: Path,
    dem_report_path: Path,
    allow_sample: bool = False,
) -> dict[str, Any]:
    dataset_report = _read_json(dataset_report_path)
    dem_report = _read_json(dem_report_path)
    checks = [
        _check_report_ok("dataset_report_ok", dataset_report),
        _check_report_ok("dem_report_ok", dem_report),
        _check_dataset_report_shape(dataset_report),
        _check_dem_report_shape(dem_report),
    ]
    if not allow_sample:
        checks.append(_check_not_sample("dataset_report_not_sample", dataset_report))
        checks.append(_check_not_sample("dem_report_not_sample", dem_report))
    passed = all(check["passed"] for check in checks)
    return {
        "schema": "real_data_acceptance_v1",
        "passed": passed,
        "dataset_report": str(dataset_report_path.resolve()),
        "dem_report": str(dem_report_path.resolve()),
        "allow_sample": allow_sample,
        "checks": checks,
        "remaining_master_plan_items": [] if passed else [
            "Test against real VWorld/GIS building data.",
            "Test against real DEM data.",
        ],
    }


def format_text_report(result: dict[str, Any]) -> str:
    lines = [f"REAL_DATA_ACCEPTANCE {'PASS' if result['passed'] else 'FAIL'}"]
    for check in result["checks"]:
        status = "PASS" if check["passed"] else "FAIL"
        lines.append(f"[{status}] {check['name']}: {check['message']}")
    if result.get("remaining_master_plan_items"):
        lines.append("Remaining:")
        for item in result["remaining_master_plan_items"]:
            lines.append(f"- {item}")
    return "\n".join(lines)


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _check_report_ok(name: str, report: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": name,
        "passed": report.get("ok") is True,
        "message": "ok=true" if report.get("ok") is True else f"ok={report.get('ok')}",
    }


def _check_dataset_report_shape(report: dict[str, Any]) -> dict[str, Any]:
    required = ("area", "buildings", "dem", "checks", "dataset_manifest")
    missing = [key for key in required if key not in report]
    return {
        "name": "dataset_report_shape",
        "passed": not missing,
        "message": "required sections present" if not missing else f"missing: {', '.join(missing)}",
    }


def _check_dem_report_shape(report: dict[str, Any]) -> dict[str, Any]:
    required = ("dem", "checks", "source")
    missing = [key for key in required if key not in report]
    return {
        "name": "dem_report_shape",
        "passed": not missing,
        "message": "required sections present" if not missing else f"missing: {', '.join(missing)}",
    }


def _check_not_sample(name: str, report: dict[str, Any]) -> dict[str, Any]:
    text = _normalized_report_text(report)
    matched = [marker for marker in SAMPLE_MARKERS if marker.lower() in text]
    return {
        "name": name,
        "passed": not matched,
        "message": "no sample fixture markers found" if not matched else f"sample markers: {', '.join(matched)}",
    }


def _normalized_report_text(report: dict[str, Any]) -> str:
    text = json.dumps(report, ensure_ascii=False).replace("\\", "/").lower()
    while "//" in text:
        text = text.replace("//", "/")
    return text


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = validate_acceptance(
            dataset_report_path=args.dataset_report,
            dem_report_path=args.dem_report,
            allow_sample=args.allow_sample,
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    if args.format == "json":
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(format_text_report(result))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
