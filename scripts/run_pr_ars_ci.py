from __future__ import annotations

import ast
import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = ROOT / "tasks"
MANIFEST_PATH = ROOT / ".cars" / "manifest.json"
DELIVERY_PATH = ROOT / ".cars" / "delivery.md"


def main() -> int:
    manifest = load_manifest()
    task = load_task(manifest["task_id"])
    changed_files = git_changed_files()

    failures: list[str] = []

    alignment_ok, reasons = alignment_passes(task, manifest, changed_files)
    failures.extend(reasons)

    reviewability_ok, reasons = reviewability_passes(task)
    failures.extend(reasons)

    safety_ok, reasons = safety_passes(task, changed_files)
    failures.extend(reasons)

    report = {
        "task_id": manifest["task_id"],
        "alignment": alignment_ok,
        "reviewability": reviewability_ok,
        "safety": safety_ok,
        "changed_files": changed_files,
        "reasons": failures,
    }

    print(json.dumps(report, indent=2))
    write_step_summary(report)
    return 1 if failures else 0


def load_manifest() -> dict[str, object]:
    if not MANIFEST_PATH.exists():
        raise SystemExit(
            "Missing .cars/manifest.json. Every PR must include task metadata."
        )
    manifest = json.loads(MANIFEST_PATH.read_text())
    if "task_id" not in manifest:
        raise SystemExit(".cars/manifest.json must include task_id.")
    if "acceptance_mapping" not in manifest:
        raise SystemExit(".cars/manifest.json must include acceptance_mapping.")
    if "touched_files" not in manifest:
        raise SystemExit(".cars/manifest.json must include touched_files.")
    return manifest


def load_task(task_id: str) -> dict[str, object]:
    task_path = TASKS_DIR / task_id / "task.json"
    if not task_path.exists():
        raise SystemExit(f"Unknown task_id {task_id!r} in .cars/manifest.json.")
    return json.loads(task_path.read_text())


def git_changed_files() -> list[str]:
    base_ref = os.environ.get("GITHUB_BASE_REF")
    if base_ref:
        subprocess.run(
            ["git", "fetch", "origin", base_ref, "--depth=1"],
            cwd=ROOT,
            capture_output=True,
            check=False,
            text=True,
        )
        diff_target = f"origin/{base_ref}...HEAD"
    else:
        diff_target = "HEAD~1..HEAD"

    result = subprocess.run(
        ["git", "diff", "--name-only", diff_target],
        cwd=ROOT,
        capture_output=True,
        check=True,
        text=True,
    )
    files = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return sorted(
        file_path
        for file_path in files
        if file_path not in {".cars/manifest.json", ".cars/delivery.md"}
    )


def alignment_passes(
    task: dict[str, object],
    manifest: dict[str, object],
    changed_files: list[str],
) -> tuple[bool, list[str]]:
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

    allowed_files = task.get("allowed_files", [])
    for changed_file in changed_files:
        if not file_matches_any_rule(changed_file, allowed_files):
            reasons.append(f"changed file outside allowed scope: {changed_file}")

    declared_files = sorted(manifest.get("touched_files", []))
    if declared_files != changed_files:
        reasons.append(
            "manifest touched_files must exactly match the PR diff excluding .cars metadata"
        )

    return not reasons, reasons


def reviewability_passes(task: dict[str, object]) -> tuple[bool, list[str]]:
    if not DELIVERY_PATH.exists():
        return False, ["missing .cars/delivery.md"]

    reasons: list[str] = []
    delivery_text = DELIVERY_PATH.read_text()
    for heading in task["required_review_sections"]:
        if f"## {heading}" not in delivery_text:
            reasons.append(f"missing review section: {heading}")
    return not reasons, reasons


def safety_passes(task: dict[str, object], changed_files: list[str]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    banned = set(task.get("banned_calls", []))

    for changed_file in changed_files:
        file_path = ROOT / changed_file
        if file_path.suffix != ".py" or not file_path.exists():
            continue
        tree = ast.parse(file_path.read_text(), filename=changed_file)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in banned:
                    reasons.append(f"banned call used in {changed_file}: {node.func.id}")
                if isinstance(node.func, ast.Attribute) and node.func.attr in banned:
                    reasons.append(f"banned call used in {changed_file}: {node.func.attr}")

    return not reasons, reasons


def file_matches_any_rule(changed_file: str, allowed_files: list[str]) -> bool:
    for allowed in allowed_files:
        if "/" in allowed:
            if changed_file == allowed:
                return True
        elif Path(changed_file).name == allowed:
            return True
    return False


def write_step_summary(report: dict[str, object]) -> None:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path is None:
        return

    lines = [
        "# CARS ARS Gate",
        "",
        f"- task_id: `{report['task_id']}`",
        f"- alignment: `{report['alignment']}`",
        f"- reviewability: `{report['reviewability']}`",
        f"- safety: `{report['safety']}`",
        "",
        "## Changed Files",
    ]

    if report["changed_files"]:
        lines.extend(f"- {file_path}" for file_path in report["changed_files"])
    else:
        lines.append("- none")

    lines.append("")
    lines.append("## Findings")
    if report["reasons"]:
        lines.extend(f"- {reason}" for reason in report["reasons"])
    else:
        lines.append("- no ARS failures detected")

    Path(summary_path).write_text("\n".join(lines))


if __name__ == "__main__":
    raise SystemExit(main())
