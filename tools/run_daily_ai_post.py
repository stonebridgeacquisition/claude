"""
Orchestrator for the daily AI post workflow.
Runs: scrape → generate → post
Used by cron for automated daily execution.
"""
import subprocess
import sys
import os
from datetime import datetime

PYTHON = sys.executable
TOOLS_DIR = os.path.dirname(__file__)

def run(script, label):
    print(f"\n[{datetime.now().isoformat()}] === {label} ===", flush=True)
    result = subprocess.run(
        [PYTHON, os.path.join(TOOLS_DIR, script)],
        capture_output=False
    )
    if result.returncode != 0:
        print(f"[FATAL] {label} failed (exit {result.returncode})", flush=True)
        sys.exit(1)

def main():
    print(f"[{datetime.now().isoformat()}] Starting daily AI post workflow", flush=True)
    run("scrape_ai_news.py",      "Phase 1: Scrape news")
    run("generate_skool_post.py", "Phase 2: Generate post")
    run("post_to_skool.py",       "Phase 3: Post to Skool")
    run("notify_telegram.py",     "Phase 4: Notify Telegram")
    print(f"\n[{datetime.now().isoformat()}] Workflow complete", flush=True)

if __name__ == "__main__":
    main()
