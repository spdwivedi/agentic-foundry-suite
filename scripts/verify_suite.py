"""Global verification runner executing all assignment scenarios and validating transcripts."""

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List
from tabulate import tabulate


REPO_ROOT = Path(__file__).resolve().parent.parent


def run_scenario(name: str, cmd: List[str], expected_file: Path) -> Dict[str, Any]:
    """Execute a single scenario subprocess and verify artifact generation."""
    start_time = time.time()
    env = dict(os.environ)

    proc = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=env,
    )
    elapsed = round(time.time() - start_time, 2)

    exit_ok = (proc.returncode == 0)
    file_ok = expected_file.exists() and expected_file.stat().st_size > 0
    passed = exit_ok and file_ok

    details = []
    if not exit_ok:
        err_msg = (proc.stderr or proc.stdout or "").strip().splitlines()
        last_line = err_msg[-1] if err_msg else f"Exit code {proc.returncode}"
        details.append(f"ERR: {last_line[:60]}")
    if not file_ok:
        details.append("File missing/empty")
    if passed:
        details.append(f"Size: {expected_file.stat().st_size} bytes")

    return {
        "scenario": name,
        "exit_code": proc.returncode,
        "artifact": str(expected_file.relative_to(REPO_ROOT)),
        "time_sec": elapsed,
        "status": "PASS" if passed else "FAIL",
        "details": "; ".join(details),
    }


def main():
    """Run full test suite across Assignments 1, 2, and 3."""
    py = sys.executable

    scenarios = [
        (
            "Assignment 1: Clean Flow",
            [py, "assignment-1/agent.py", "--run-clean"],
            REPO_ROOT / "assignment-1" / "transcripts" / "transcript_1_clean.txt",
        ),
        (
            "Assignment 1: Failure Recovery",
            [py, "assignment-1/agent.py", "--run-failure"],
            REPO_ROOT / "assignment-1" / "transcripts" / "transcript_2_failure_recovery.txt",
        ),
        (
            "Assignment 2: Approved Gate",
            [py, "assignment-2/agent.py", "--scenario", "pass"],
            REPO_ROOT / "assignment-2" / "transcripts" / "transcript_1_approved.txt",
        ),
        (
            "Assignment 2: Rejected Gate",
            [py, "assignment-2/agent.py", "--scenario", "fail"],
            REPO_ROOT / "assignment-2" / "transcripts" / "transcript_2_rejected.txt",
        ),
        (
            "Assignment 3: Interrupted Pipeline",
            [py, "assignment-3/agent.py", "--interrupt-after", "2"],
            REPO_ROOT / "assignment-3" / "state_store" / "agent_state.db",
        ),
        (
            "Assignment 3: Resumed Pipeline",
            [py, "assignment-3/agent.py", "--resume"],
            REPO_ROOT / "assignment-3" / "transcripts" / "transcript_1_resumed.txt",
        ),
        (
            "Assignment 3: Corrupt Item Self-Check",
            [py, "assignment-3/agent.py", "--corrupt-item", "3"],
            REPO_ROOT / "assignment-3" / "transcripts" / "transcript_2_validation_failed.txt",
        ),
    ]

    print("=" * 80)
    print("STARTING GLOBAL TEST SUITE (7 SCENARIOS)")
    print("=" * 80)

    results: List[Dict[str, Any]] = []
    all_passed = True

    for name, cmd, expected_file in scenarios:
        print(f"Executing: {name} ...", end=" ", flush=True)
        res = run_scenario(name, cmd, expected_file)
        results.append(res)
        print(f"[{res['status']}] ({res['time_sec']}s)")
        if res["status"] != "PASS":
            all_passed = False

    table_data = [
        [
            r["scenario"],
            r["status"],
            r["exit_code"],
            f"{r['time_sec']}s",
            r["artifact"],
            r["details"],
        ]
        for r in results
    ]

    headers = ["Scenario", "Status", "Code", "Duration", "Target Artifact", "Details"]
    print("\n" + tabulate(table_data, headers=headers, tablefmt="github") + "\n")

    if all_passed:
        print("[SUCCESS] All 7 scenarios passed verification. Suite is fully green.")
        sys.exit(0)
    else:
        print("[FAILURE] One or more scenarios failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
