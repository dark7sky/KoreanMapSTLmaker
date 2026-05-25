import argparse
import json
import re
from pathlib import Path
from typing import Any


TASK_PATTERN = re.compile(r"^- \[(?P<mark>[ xX])\] (?P<title>.+)$")
PHASE_PATTERN = re.compile(r"^## (?P<title>.+)$")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize checkbox progress from docs/MASTER_PLAN.md.")
    parser.add_argument("--plan", type=Path, default=Path("docs/MASTER_PLAN.md"), help="Markdown plan file.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of a text summary.")
    return parser.parse_args(argv)


def summarize_plan(plan_path: Path) -> dict[str, Any]:
    phase = "Uncategorized"
    phases: dict[str, dict[str, Any]] = {}
    for line in plan_path.read_text(encoding="utf-8").splitlines():
        phase_match = PHASE_PATTERN.match(line)
        if phase_match:
            phase = phase_match.group("title")
            phases.setdefault(phase, _empty_phase())
            continue

        task_match = TASK_PATTERN.match(line)
        if not task_match:
            continue
        phases.setdefault(phase, _empty_phase())
        done = task_match.group("mark").lower() == "x"
        phases[phase]["total"] += 1
        phases[phase]["done"] += int(done)
        if not done:
            phases[phase]["remaining_tasks"].append(task_match.group("title"))

    total = sum(item["total"] for item in phases.values())
    done = sum(item["done"] for item in phases.values())
    remaining = total - done
    percent = 0.0 if total == 0 else round((done / total) * 100, 1)
    return {
        "plan": str(plan_path),
        "total": total,
        "done": done,
        "remaining": remaining,
        "percent_done": percent,
        "phases": phases,
    }


def format_text(summary: dict[str, Any]) -> str:
    lines = [
        f"Plan: {summary['plan']}",
        f"Overall: {summary['done']}/{summary['total']} done ({summary['percent_done']}%), {summary['remaining']} remaining",
        "",
    ]
    for phase, data in summary["phases"].items():
        total = data["total"]
        done = data["done"]
        percent = 0.0 if total == 0 else round((done / total) * 100, 1)
        lines.append(f"{phase}: {done}/{total} done ({percent}%)")
        for task in data["remaining_tasks"][:5]:
            lines.append(f"  - {task}")
        omitted = len(data["remaining_tasks"]) - 5
        if omitted > 0:
            lines.append(f"  - ... {omitted} more")
    return "\n".join(lines)


def _empty_phase() -> dict[str, Any]:
    return {"total": 0, "done": 0, "remaining_tasks": []}


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    summary = summarize_plan(args.plan)
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(format_text(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
