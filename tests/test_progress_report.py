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
                "## Phase 1",
                "- [x] Done task",
                "- [ ] Remaining task",
                "## Phase 2",
                "- [X] Also done",
            ]
        ),
        encoding="utf-8",
    )

    summary = progress_report.summarize_plan(plan_path)

    assert summary["total"] == 3
    assert summary["done"] == 2
    assert summary["remaining"] == 1
    assert summary["percent_done"] == 66.7
    assert summary["phases"]["Phase 1"]["remaining_tasks"] == ["Remaining task"]


def test_format_text_includes_overall_progress(tmp_path):
    plan_path = tmp_path / "MASTER_PLAN.md"
    plan_path.write_text("## Phase\n- [x] Done\n- [ ] Left\n", encoding="utf-8")

    text = progress_report.format_text(progress_report.summarize_plan(plan_path))

    assert "Overall: 1/2 done (50.0%), 1 remaining" in text
    assert "Phase: 1/2 done (50.0%)" in text


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
