#!/usr/bin/env python3
"""STRC dashboard daily refresh: fetch Yahoo data, bake, commit, push.

Silent (exit 0, no output) when nothing material changed — prices/dividends
identical to HEAD — so weekend runs don't spam. Non-zero exit on failure so
the Hermes cron scheduler raises an error alert.

Usage:
    python scripts/refresh_cron.py            # fetch + bake + commit + push
    python scripts/refresh_cron.py --dry-run  # run pipeline, report, restore tree
"""
import datetime
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = "https://nwfella.github.io/strc-dividend-calculator/"


def head_data():
    try:
        out = subprocess.run(["git", "show", "HEAD:data/strc_data.json"],
                             capture_output=True, text=True, check=True, cwd=ROOT).stdout
        return json.loads(out)
    except Exception:
        return None


def fingerprint(d):
    return (json.dumps(d.get("prices", []), sort_keys=True),
            json.dumps(d.get("dividends", []), sort_keys=True))


def run(cmd, **kw):
    env = dict(os.environ)
    env["GIT_TERMINAL_PROMPT"] = "0"  # fail fast instead of hanging on credential prompt
    return subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, env=env, **kw)


def main():
    dry = "--dry-run" in sys.argv
    before = head_data()

    r = run([sys.executable, "scripts/update_data.py", "--bake"])
    if r.returncode != 0:
        print("STRC refresh FAILED (fetch):\n" + (r.stdout + r.stderr).strip())
        return 1

    with open(os.path.join(ROOT, "data", "strc_data.json"), encoding="utf-8") as f:
        after = json.load(f)

    if before is not None and fingerprint(before) == fingerprint(after):
        # Nothing material changed (meta.as_of always moves) — keep tree clean, stay silent.
        run(["git", "restore", "--worktree", "data/strc_data.json", "index.html"])
        return 0

    meta = after["meta"]
    prev = before["meta"]["last_close"] if before else None
    summary = ("STRC refresh %s: close $%.2f (prev $%.2f), %d dividends — %s"
               % (meta.get("last_close_date"), meta.get("last_close") or 0,
                  prev or 0, len(after["dividends"]), PAGE))

    if dry:
        run(["git", "restore", "--worktree", "data/strc_data.json", "index.html"])
        print("[dry-run] " + summary)
        return 0

    date = datetime.date.today().isoformat()
    run(["git", "add", "data/strc_data.json", "index.html"])
    c = run(["git", "commit", "-m", "data refresh %s" % date])
    if c.returncode != 0:
        print("STRC refresh FAILED (commit):\n" + (c.stdout + c.stderr).strip())
        return 1
    p = run(["git", "push"])
    if p.returncode != 0:
        print("STRC refresh: committed but PUSH FAILED:\n" + (p.stdout + p.stderr).strip())
        return 1
    print(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
