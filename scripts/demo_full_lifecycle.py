"""
Demo Script: Full Task Lifecycle on Algorand TestNet

Run this script to execute 10 real tasks through the platform and
capture evidence (transaction IDs, explorer links) for the hackathon submission.

Prerequisites:
  - Backend running on localhost:3001
  - ADMIN_MNEMONIC set in .env
  - Funded testnet account (use https://bank.testnet.algorand.network/)

Usage:
  python scripts/demo_full_lifecycle.py

Output:
  - Prints explorer links for each transaction
  - Saves evidence to evidence/TESTNET_EXECUTIONS.md
"""

import os
import sys
import json
import time
import uuid
from pathlib import Path
from datetime import datetime

import requests
from dotenv import load_dotenv

# Load environment
_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(_ROOT / ".env")

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:3001")
ADMIN_ADDRESS = os.environ.get("ADMIN_ADDRESS")
EXPLORER_BASE = "https://testnet.explorer.perawallet.app"

# 10 demo task descriptions across all 4 lanes
DEMO_TASKS = [
    {"description": "Research the top 5 DeFi protocols on Algorand by TVL", "lane": "RESEARCH", "bounty": 5000000},
    {"description": "Analyze sentiment of Algorand community on Twitter this week", "lane": "RESEARCH", "bounty": 3000000},
    {"description": "Write a Python function to calculate compound interest with daily accrual", "lane": "CODE", "bounty": 4000000},
    {"description": "Debug this TypeScript error: cannot assign to read-only property", "lane": "CODE", "bounty": 3000000},
    {"description": "Build a REST API endpoint for user registration with validation", "lane": "CODE", "bounty": 6000000},
    {"description": "Clean this CSV dataset: remove nulls, normalize dates, deduplicate", "lane": "DATA", "bounty": 4000000},
    {"description": "Create a summary statistics report from this sales data", "lane": "DATA", "bounty": 3000000},
    {"description": "Write a Twitter thread announcing our new DeFi product launch", "lane": "OUTREACH", "bounty": 3000000},
    {"description": "Draft a partnership outreach email to 3 Algorand ecosystem projects", "lane": "OUTREACH", "bounty": 4000000},
    {"description": "Research and summarize the x402 payment protocol specification", "lane": "RESEARCH", "bounty": 5000000},
]


def check_backend():
    """Verify backend is running."""
    try:
        resp = requests.get(f"{BACKEND_URL}/health", timeout=5)
        if resp.status_code == 200:
            print(f"✅ Backend is running at {BACKEND_URL}")
            return True
    except requests.exceptions.ConnectionError:
        pass
    print(f"❌ Backend not reachable at {BACKEND_URL}")
    print("   Start the backend with: npm run dev (in dojo-backend/)")
    return False


def create_task(task_data: dict, index: int) -> dict | None:
    """Create a task via the backend API."""
    task_id = f"demo-{uuid.uuid4().hex[:8]}"
    payload = {
        "id": task_id,
        "title": f"Demo Task {index + 1}",
        "description": task_data["description"],
        "lane": task_data["lane"],
        "bountyUsdc": task_data["bounty"],
        "clientAddress": ADMIN_ADDRESS,
        "deadlineDays": 7,
    }

    try:
        resp = requests.post(f"{BACKEND_URL}/api/tasks", json=payload, timeout=30)
        if resp.status_code == 201:
            result = resp.json()
            print(f"  ✅ Task {index + 1} created: {result.get('id', task_id)}")
            return result
        else:
            print(f"  ⚠️  Task {index + 1} failed ({resp.status_code}): {resp.text[:100]}")
            return None
    except Exception as e:
        print(f"  ❌ Task {index + 1} error: {e}")
        return None


def poll_task_result(task_id: str, max_wait: int = 120) -> dict | None:
    """Poll for task completion."""
    start = time.time()
    while time.time() - start < max_wait:
        try:
            resp = requests.get(f"{BACKEND_URL}/api/tasks/{task_id}", timeout=10)
            if resp.status_code == 200:
                task = resp.json()
                state = task.get("state", "UNKNOWN")
                if state in ("SUBMITTED", "VERIFIED", "SETTLED"):
                    return task
                elif state == "SLASHED":
                    return task
        except Exception:
            pass
        time.sleep(5)
    return None


def generate_evidence(results: list[dict]) -> str:
    """Generate evidence markdown file."""
    lines = [
        "# TestNet Execution Evidence",
        "",
        f"**Generated**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
        f"**Tasks Executed**: {len(results)}",
        f"**Network**: Algorand TestNet",
        "",
        "---",
        "",
        "## Execution Log",
        "",
        "| # | Task ID | Lane | State | Description |",
        "|---|---------|------|-------|-------------|",
    ]

    for i, r in enumerate(results):
        task_id = r.get("id", "?")[:16]
        lane = r.get("lane", "?")
        state = r.get("state", "?")
        desc = (r.get("description") or r.get("title") or "?")[:40]
        lines.append(f"| {i+1} | `{task_id}...` | {lane} | {state} | {desc}... |")

    lines.extend([
        "",
        "---",
        "",
        "## On-Chain Verification",
        "",
        f"- EscrowVault App: [{EXPLORER_BASE}/application/761941677]({EXPLORER_BASE}/application/761941677)",
        f"- DojoRegistry App: [{EXPLORER_BASE}/application/758815322]({EXPLORER_BASE}/application/758815322)",
        f"- CommitmentLock App: [{EXPLORER_BASE}/application/761941684]({EXPLORER_BASE}/application/761941684)",
        f"- PayoutSplitter App: [{EXPLORER_BASE}/application/758815334]({EXPLORER_BASE}/application/758815334)",
        "",
        "## Summary",
        "",
        f"- Total tasks created: {len(results)}",
        f"- Successfully completed: {sum(1 for r in results if r.get('state') in ('SUBMITTED', 'VERIFIED', 'SETTLED'))}",
        f"- Failed/Slashed: {sum(1 for r in results if r.get('state') == 'SLASHED')}",
        f"- Pending: {sum(1 for r in results if r.get('state') in ('CREATED', 'LOCKED'))}",
    ])

    return "\n".join(lines)


def main():
    print("=" * 60)
    print("  0rca Swarm Dojo — TestNet Execution Demo")
    print("=" * 60)
    print()

    if not ADMIN_ADDRESS:
        print("❌ ADMIN_ADDRESS not set in .env")
        sys.exit(1)

    if not check_backend():
        sys.exit(1)

    print()
    print(f"Running {len(DEMO_TASKS)} demo tasks...")
    print()

    results = []
    for i, task_data in enumerate(DEMO_TASKS):
        print(f"[{i+1}/{len(DEMO_TASKS)}] {task_data['lane']}: {task_data['description'][:50]}...")
        result = create_task(task_data, i)
        if result:
            results.append(result)
        time.sleep(2)  # Small delay between tasks

    print()
    print(f"Created {len(results)}/{len(DEMO_TASKS)} tasks. Waiting for AI execution...")
    print()

    # Poll for results (wait up to 2 min per task)
    final_results = []
    for i, r in enumerate(results):
        task_id = r.get("id")
        if not task_id:
            final_results.append(r)
            continue
        print(f"  Polling task {i+1}/{len(results)} ({task_id[:12]}...)...", end=" ")
        completed = poll_task_result(task_id, max_wait=120)
        if completed:
            print(f"→ {completed.get('state', '?')}")
            final_results.append(completed)
        else:
            print(f"→ TIMEOUT (still pending)")
            final_results.append(r)

    # Generate evidence
    evidence_md = generate_evidence(final_results)
    evidence_path = _ROOT / "evidence" / "TESTNET_EXECUTIONS.md"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(evidence_md, encoding="utf-8")

    print()
    print("=" * 60)
    print(f"  Evidence saved to: {evidence_path}")
    print("=" * 60)
    print()

    # Print summary
    completed_count = sum(1 for r in final_results if r.get("state") in ("SUBMITTED", "VERIFIED", "SETTLED"))
    print(f"Results: {completed_count}/{len(final_results)} tasks completed successfully")
    print(f"Explorer: {EXPLORER_BASE}/application/761941677")


if __name__ == "__main__":
    main()
