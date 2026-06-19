from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.auto_build import auto_build
from scripts.list_datasets import summarize_registry
from scripts.progress_report import summarize_plan


REQUIRED_FILES = (
    "README.md",
    "requirements.txt",
    "datasets.sample.json",
    "docs/WORKFLOW.md",
    "docs/DATASETS.md",
    "docs/REAL_DATA_GUIDE.md",
    "docs/WEB_SERVICE.md",
    "docs/MASTER_PLAN.md",
)
ACCEPTANCE_EVIDENCE_PATH = Path("output/real_data_acceptance.json")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run local release-readiness checks before publishing.")
    parser.add_argument("--skip-tests", action="store_true", help="Skip pytest to run a faster static/sample check.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of a text report.")
    return parser.parse_args(argv)


def run_release_checks(*, run_tests: bool = True) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    checks.append(_required_files_check())
    checks.append(_progress_check())
    checks.append(_sample_registry_check())
    checks.append(_sample_auto_build_check())
    checks.append(_real_data_acceptance_evidence_check())
    if run_tests:
        checks.append(_pytest_check())
    passed = all(check["passed"] for check in checks)
    return {"passed": passed, "checks": checks}


def format_text_report(report: dict[str, Any]) -> str:
    lines = [f"RELEASE_CHECK {'PASS' if report['passed'] else 'FAIL'}"]
    for check in report["checks"]:
        status = "PASS" if check["passed"] else "FAIL"
        lines.append(f"[{status}] {check['name']}: {check['message']}")
        for detail in check.get("details", [])[:8]:
            lines.append(f"  - {detail}")
    return "\n".join(lines)


def _required_files_check() -> dict[str, Any]:
    missing = [path for path in REQUIRED_FILES if not Path(path).exists()]
    return {
        "name": "required_files",
        "passed": not missing,
        "message": "all required files present" if not missing else f"{len(missing)} missing",
        "details": missing,
    }


def _progress_check() -> dict[str, Any]:
    summary = summarize_plan(Path("docs/MASTER_PLAN.md"))
    remaining = summary["remaining"]
    expected_remaining = {
        "Test against real VWorld/GIS building data.",
        "Test against real DEM data.",
    }
    actual_remaining = {
        task
        for phase in summary["phases"].values()
        for task in phase["remaining_tasks"]
    }
    passed = remaining == 2 and actual_remaining == expected_remaining
    return {
        "name": "master_plan_progress",
        "passed": passed,
        "message": f"{summary['done']}/{summary['total']} done; {remaining} remaining",
        "details": sorted(actual_remaining),
    }


def _sample_registry_check() -> dict[str, Any]:
    summary = summarize_registry(Path("datasets.sample.json"))
    missing = []
    for dataset in summary.get("datasets", []):
        missing.extend(f"{dataset['name']}.{field}" for field in dataset.get("missing_paths", []))
    return {
        "name": "sample_registry",
        "passed": summary.get("exists") is True and summary.get("dataset_count") == 1 and not missing,
        "message": f"{summary.get('dataset_count', 0)} sample dataset(s)",
        "details": missing,
    }


def _sample_auto_build_check() -> dict[str, Any]:
    try:
        report = auto_build(
            area_path=Path("data/sample/area.geojson"),
            registry_path=Path("datasets.sample.json"),
            dry_run=True,
        )
    except Exception as exc:
        return {"name": "sample_auto_build", "passed": False, "message": str(exc), "details": []}
    return {
        "name": "sample_auto_build",
        "passed": report["status"] == "validated" and report["validation"]["ok"] is True,
        "message": f"status={report['status']}; dataset={report['dataset']['name']}",
        "details": report["validation"].get("errors", []),
    }


def _real_data_acceptance_evidence_check() -> dict[str, Any]:
    if not ACCEPTANCE_EVIDENCE_PATH.exists():
        return {
            "name": "real_data_acceptance_evidence",
            "passed": True,
            "message": "not present; final 2 master-plan items still require external real data",
            "details": [],
        }
    try:
        payload = json.loads(ACCEPTANCE_EVIDENCE_PATH.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        return {
            "name": "real_data_acceptance_evidence",
            "passed": False,
            "message": f"could not read evidence: {exc}",
            "details": [],
        }
    checks = payload.get("checks", [])
    failed = [
        f"{check.get('name')}: {check.get('message')}"
        for check in checks
        if isinstance(check, dict) and not check.get("passed")
    ]
    return {
        "name": "real_data_acceptance_evidence",
        "passed": payload.get("passed") is True,
        "message": "real-data evidence accepted" if payload.get("passed") is True else "real-data evidence failed",
        "details": failed,
    }


def _pytest_check() -> dict[str, Any]:
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "--basetemp", ".pytest_tmp_release_check"],
        capture_output=True,
        text=True,
        check=False,
    )
    output = (completed.stdout + "\n" + completed.stderr).strip()
    tail = output.splitlines()[-8:]
    return {
        "name": "pytest",
        "passed": completed.returncode == 0,
        "message": f"exit_code={completed.returncode}",
        "details": tail,
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = run_release_checks(run_tests=not args.skip_tests)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(format_text_report(report))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
