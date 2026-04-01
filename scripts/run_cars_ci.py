from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cars_eval.evaluate import TASKS_DIR, evaluate_task, load_task


def main() -> int:
    task_ids = discover_ci_tasks()
    if not task_ids:
        print("No benchmark tasks with ci_expectations were found.")
        return 0

    reports: list[dict[str, object]] = []
    failures: list[str] = []

    for task_id in task_ids:
        report = evaluate_task(task_id)
        reports.append(report)
        failures.extend(compare_with_expectations(task_id, report))

    print(json.dumps({"reports": reports}, indent=2))
    write_step_summary(reports, failures)

    if failures:
        print("\nCARS CI failures:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1

    return 0


def discover_ci_tasks() -> list[str]:
    task_ids: list[str] = []
    for task_dir in sorted(path for path in TASKS_DIR.iterdir() if path.is_dir()):
        task = load_task(task_dir.name)
        if "ci_expectations" in task:
            task_ids.append(task_dir.name)
    return task_ids


def compare_with_expectations(task_id: str, report: dict[str, object]) -> list[str]:
    task = load_task(task_id)
    expected = task["ci_expectations"]
    failures: list[str] = []

    for key in ("raw_resolve_rate", "team_usable_delivery_rate"):
        actual = report[key]
        if actual != expected[key]:
            failures.append(
                f"{task_id}: expected {key}={expected[key]!r}, got {actual!r}"
            )

    actual_results = {
        result["submission_id"]: result
        for result in report["results"]
    }
    expected_submissions = expected.get("submissions", {})
    extra_submissions = sorted(set(actual_results) - set(expected_submissions))
    if extra_submissions:
        failures.append(
            f"{task_id}: unexpected submissions in report: {', '.join(extra_submissions)}"
        )
    for submission_id, submission_expectations in expected_submissions.items():
        actual = actual_results.get(submission_id)
        if actual is None:
            failures.append(f"{task_id}: missing submission {submission_id!r} in report")
            continue
        for key, expected_value in submission_expectations.items():
            if actual.get(key) != expected_value:
                failures.append(
                    f"{task_id}/{submission_id}: expected {key}={expected_value!r}, "
                    f"got {actual.get(key)!r}"
                )

    return failures


def write_step_summary(reports: list[dict[str, object]], failures: list[str]) -> None:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path is None:
        return
    lines = ["# CARS Benchmark", ""]
    for report in reports:
        lines.append(f"## {report['task_id']}")
        lines.append(
            f"- raw_resolve_rate: `{report['raw_resolve_rate']}`"
        )
        lines.append(
            f"- team_usable_delivery_rate: `{report['team_usable_delivery_rate']}`"
        )
        for result in report["results"]:
            lines.append(
                f"- {result['submission_id']}: "
                f"correctness={result['correctness']}, "
                f"alignment={result['alignment']}, "
                f"reviewability={result['reviewability']}, "
                f"safety={result['safety']}, "
                f"team_usable={result['team_usable']}"
            )
        lines.append("")
    if failures:
        lines.append("## Failures")
        for failure in failures:
            lines.append(f"- {failure}")
    Path(summary_path).write_text("\n".join(lines))


if __name__ == "__main__":
    raise SystemExit(main())
