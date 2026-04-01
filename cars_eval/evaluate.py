from __future__ import annotations

import argparse
import ast
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from difflib import unified_diff
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = ROOT / "tasks"
BASELINE_FILE = ROOT / "src" / "cars_store" / "pricing.py"


@dataclass
class SubmissionResult:
    submission_id: str
    correctness: bool
    alignment: bool
    reviewability: bool
    safety: bool
    rework_proxy: bool
    team_usable: bool
    reasons: list[str]

    def as_dict(self) -> dict[str, object]:
        return {
            "submission_id": self.submission_id,
            "correctness": self.correctness,
            "alignment": self.alignment,
            "reviewability": self.reviewability,
            "safety": self.safety,
            "rework_proxy": self.rework_proxy,
            "team_usable": self.team_usable,
            "reasons": self.reasons,
        }


def load_task(task_id: str) -> dict[str, object]:
    task_file = TASKS_DIR / task_id / "task.json"
    return json.loads(task_file.read_text())


def run_tests(candidate_file: Path) -> tuple[bool, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    env["CARS_PRICING_PATH"] = str(candidate_file)
    cmd = [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", "."]
    result = subprocess.run(
        cmd,
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    output = (result.stdout + "\n" + result.stderr).strip()
    return result.returncode == 0, output


def alignment_passes(task: dict[str, object], manifest: dict[str, object]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    required_ids = {criterion["id"] for criterion in task["acceptance_criteria"]}
    provided_ids = set(manifest.get("acceptance_mapping", {}).keys())
    if required_ids != provided_ids:
        missing = sorted(required_ids - provided_ids)
        extra = sorted(provided_ids - required_ids)
        if missing:
            reasons.append(f"missing acceptance mappings: {', '.join(missing)}")
        if extra:
            reasons.append(f"unexpected acceptance mappings: {', '.join(extra)}")

    allowed_files = set(task["allowed_files"])
    touched_files = set(manifest.get("touched_files", []))
    if not touched_files.issubset(allowed_files):
        reasons.append("submission changed files outside the allowed scope")

    return not reasons, reasons


def reviewability_passes(task: dict[str, object], submission_dir: Path) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    delivery_text = (submission_dir / "delivery.md").read_text()
    for heading in task["required_review_sections"]:
        if f"## {heading}" not in delivery_text:
            reasons.append(f"missing review section: {heading}")
    return not reasons, reasons


def safety_passes(task: dict[str, object], candidate_file: Path) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    tree = ast.parse(candidate_file.read_text())
    banned = set(task["banned_calls"])

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in banned:
                reasons.append(f"banned call used: {node.func.id}")
            if isinstance(node.func, ast.Attribute) and node.func.attr in banned:
                reasons.append(f"banned call used: {node.func.attr}")

    return not reasons, reasons


def rework_passes(task: dict[str, object], manifest: dict[str, object], candidate_file: Path) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    limits = task["rework_limits"]
    touched_count = len(manifest.get("touched_files", []))
    if touched_count > limits["max_touched_files"]:
        reasons.append(
            f"touched {touched_count} files, limit is {limits['max_touched_files']}"
        )

    baseline_lines = BASELINE_FILE.read_text().splitlines()
    candidate_lines = candidate_file.read_text().splitlines()
    changed_lines = sum(
        1
        for line in unified_diff(baseline_lines, candidate_lines, lineterm="")
        if line.startswith("+") or line.startswith("-")
    )
    if changed_lines > limits["max_changed_lines"]:
        reasons.append(
            f"changed {changed_lines} lines, limit is {limits['max_changed_lines']}"
        )

    return not reasons, reasons


def evaluate_submission(task_id: str, submission_id: str) -> SubmissionResult:
    task = load_task(task_id)
    submission_dir = TASKS_DIR / task_id / "submissions" / submission_id
    candidate_file = submission_dir / "pricing.py"
    manifest = json.loads((submission_dir / "manifest.json").read_text())

    reasons: list[str] = []

    correctness, test_output = run_tests(candidate_file)
    if not correctness:
        reasons.append("tests failed")
        reasons.append(test_output)

    alignment, alignment_reasons = alignment_passes(task, manifest)
    reasons.extend(alignment_reasons)

    reviewability, reviewability_reasons = reviewability_passes(task, submission_dir)
    reasons.extend(reviewability_reasons)

    safety, safety_reasons = safety_passes(task, candidate_file)
    reasons.extend(safety_reasons)

    rework_proxy, rework_reasons = rework_passes(task, manifest, candidate_file)
    reasons.extend(rework_reasons)

    team_usable = all([correctness, alignment, reviewability, safety])

    return SubmissionResult(
        submission_id=submission_id,
        correctness=correctness,
        alignment=alignment,
        reviewability=reviewability,
        safety=safety,
        rework_proxy=rework_proxy,
        team_usable=team_usable,
        reasons=reasons,
    )


def evaluate_task(task_id: str, submission_ids: list[str] | None = None) -> dict[str, object]:
    submissions_root = TASKS_DIR / task_id / "submissions"
    if submission_ids is None:
        submission_ids = sorted(path.name for path in submissions_root.iterdir() if path.is_dir())

    results = [evaluate_submission(task_id, submission_id) for submission_id in submission_ids]
    resolved = sum(1 for result in results if result.correctness)
    team_usable = sum(1 for result in results if result.team_usable)

    return {
        "task_id": task_id,
        "raw_resolve_rate": resolved / len(results) if results else 0.0,
        "team_usable_delivery_rate": team_usable / len(results) if results else 0.0,
        "results": [result.as_dict() for result in results],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate coding-agent submissions with CARS.")
    parser.add_argument("--task", required=True, help="Task id to evaluate")
    parser.add_argument("--submission", help="Specific submission id to evaluate")
    parser.add_argument("--all", action="store_true", help="Evaluate all submissions for the task")
    args = parser.parse_args()

    if args.submission and args.all:
        parser.error("Use either --submission or --all, not both.")

    submission_ids = None if args.all or not args.submission else [args.submission]
    report = evaluate_task(args.task, submission_ids=submission_ids)
    print(json.dumps(report, indent=2))
    return 0
