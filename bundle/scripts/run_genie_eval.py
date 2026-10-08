"""Run a Genie Agent's benchmarks and fail when accuracy is below a threshold.

Used by CI after the agents are deployed, and locally:

    uv run bundle/scripts/run_genie_eval.py market_analyst -t dev --profile <profile>

It asks `bundle summary` for the target's space ID, starts a benchmark evaluation
run over every benchmark stored in the space (Chat mode), waits for it, and writes a
Markdown report to stdout and, in GitHub Actions, to the job summary. Accuracy is
correct answers over all benchmark questions; questions that need manual review
count as not correct. Exits 1 when accuracy is below --min-accuracy.
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path


def databricks(profile: str | None, *args: str) -> dict:
    cmd = ["databricks", *args, "-o", "json"] + (["--profile", profile] if profile else [])
    return json.loads(subprocess.run(cmd, check=True, capture_output=True, text=True).stdout)


def space_id_for(key: str, target: str, profile: str | None) -> str:
    resources = databricks(profile, "bundle", "summary", "-t", target)["resources"]
    space = resources.get("genie_spaces", {}).get(key)
    if not space or not space.get("id"):
        sys.exit(f"Genie space '{key}' is not deployed in target '{target}'; run bundle deploy first.")
    return space["id"]


def run_eval(space_id: str, profile: str | None, timeout_s: int) -> dict:
    run = databricks(profile, "genie", "genie-create-eval-run", space_id, "--json", "{}")
    run_id = run["eval_run_id"]
    deadline = time.monotonic() + timeout_s
    while run["eval_run_status"] == "RUNNING":
        if time.monotonic() > deadline:
            sys.exit(f"Evaluation run {run_id} did not finish within {timeout_s} s.")
        time.sleep(10)
        run = databricks(profile, "genie", "genie-get-eval-run", space_id, run_id)
    if run["eval_run_status"] != "DONE":
        sys.exit(f"Evaluation run {run_id} ended as {run['eval_run_status']}.")
    return run


def results(space_id: str, run_id: str, profile: str | None) -> list[dict]:
    rows, token = [], None
    while True:
        page = databricks(profile, "genie", "genie-list-eval-results", space_id, run_id,
                          *(["--page-token", token] if token else []))
        for r in page.get("eval_results", []):
            d = databricks(profile, "genie", "genie-get-eval-result-details", space_id, run_id, r["result_id"])
            rows.append({"question": r.get("question", ""), "assessment": d.get("assessment", "UNKNOWN"),
                         "reasons": d.get("assessment_reasons", [])})
        token = page.get("next_page_token")
        if not token:
            return rows


def report(key: str, target: str, run: dict, rows: list[dict], accuracy: float, min_accuracy: float) -> str:
    verdict = "passed" if accuracy >= min_accuracy else "FAILED"
    lines = [
        f"## Genie benchmarks: {key} ({target})",
        "",
        f"**Accuracy {accuracy:.0%}** ({run['num_correct']} of {run['num_questions']} correct, "
        f"{run['num_needs_review']} need review); threshold {min_accuracy:.0%}: **{verdict}**. "
        f"Eval run `{run['eval_run_id']}`.",
        "",
        "| Result | Question | Reasons |",
        "|---|---|---|",
    ]
    order = {"BAD": 0, "NEEDS_REVIEW": 1, "GOOD": 2}
    for r in sorted(rows, key=lambda r: order.get(r["assessment"], 1)):
        question = r["question"].replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {r['assessment']} | {question} | {', '.join(r['reasons'])} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a Genie Agent's benchmarks and check accuracy.")
    parser.add_argument("key", help="resource key under genie_spaces, e.g. market_analyst")
    parser.add_argument("-t", "--target", default="dev")
    parser.add_argument("--profile", help="CLI profile; omit in CI, where DATABRICKS_* variables authenticate")
    parser.add_argument("--min-accuracy", type=float, default=0.8)
    parser.add_argument("--timeout", type=int, default=900, help="seconds to wait for the run")
    args = parser.parse_args()
    os.chdir(Path(__file__).resolve().parent.parent)  # bundle root, so it runs from any folder

    space_id = space_id_for(args.key, args.target, args.profile)
    run = run_eval(space_id, args.profile, args.timeout)
    accuracy = run["num_correct"] / run["num_questions"] if run["num_questions"] else 0.0
    text = report(args.key, args.target, run, results(space_id, run["eval_run_id"], args.profile),
                  accuracy, args.min_accuracy)

    print(text)
    if summary := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(summary, "a") as f:
            f.write(text)
    if accuracy < args.min_accuracy:
        sys.exit(1)


if __name__ == "__main__":
    main()
