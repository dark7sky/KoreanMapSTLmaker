import json
import subprocess
import sys
from pathlib import Path

from scripts import progress_report


def test_summarize_plan_counts_phase_tasks(tmp_path):
    plan_path = tmp_path / "MASTER_PLAN.md"
    plan_path.write_text(
        "\n".join(
            [
                "# Plan",
                "## Phase 12 - Optional Web Service",
                "### Backend",
                "- [x] FastAPI backend",
                "  - [ ] Job API",
                "  - [ ] Upload/download endpoints",
                "### Frontend",
                "* [ ] React frontend",
                "* [ ] Local Docker packaging",
                "## Phase 13 - Data Acquisition Automation",
                "+ [X] Add environment configuration",
            ]
        ),
        encoding="utf-8",
    )

    summary = progress_report.summarize_plan(plan_path)

    assert summary["total"] == 6
    assert summary["done"] == 2
    assert summary["remaining"] == 4
    assert summary["percent_done"] == 33.3
    assert summary["phases"]["Phase 12 - Optional Web Service"]["total"] == 5
    assert summary["phases"]["Phase 12 - Optional Web Service"]["done"] == 1
    assert summary["phases"]["Phase 12 - Optional Web Service"]["remaining_tasks"] == [
        "Job API",
        "Upload/download endpoints",
        "React frontend",
        "Local Docker packaging",
    ]
    assert summary["phases"]["Phase 13 - Data Acquisition Automation"]["remaining_tasks"] == []


def test_format_text_includes_overall_progress(tmp_path):
    plan_path = tmp_path / "MASTER_PLAN.md"
    plan_path.write_text(
        "\n".join(
            [
                "## Phase 12 - Optional Web Service",
                "- [x] FastAPI backend",
                "- [ ] Job API",
                "- [ ] Upload/download endpoints",
            ]
        ),
        encoding="utf-8",
    )

    text = progress_report.format_text(progress_report.summarize_plan(plan_path))

    assert "Overall: 1/3 done (33.3%), 2 remaining" in text
    assert "Phase 12 - Optional Web Service: 1/3 done (33.3%)" in text
    assert "  - Job API" in text
    assert "  - Upload/download endpoints" in text


def test_cli_json_output(tmp_path):
    plan_path = tmp_path / "MASTER_PLAN.md"
    plan_path.write_text("## Phase\n- [x] Done\n", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(Path("scripts") / "progress_report.py"), "--plan", str(plan_path), "--json"],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)
    assert payload["done"] == 1
    assert payload["percent_done"] == 100.0
