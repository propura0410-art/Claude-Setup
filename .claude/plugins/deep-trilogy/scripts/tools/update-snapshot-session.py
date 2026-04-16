#!/usr/bin/env python3
"""Sync snapshot session_id to current session for safe /clear.

Finds the nearest snapshot.json, updates session_id and updated_at.
Does NOT modify resume_step or other workflow state — that's the
workflow's responsibility at milestones.

Usage:
    python3 update-snapshot-session.py --session-id <id> [--cwd <path>]

Output: JSON to stdout
    {"status": "synced", "snapshot_path": "...", "session_id": "..."}
    {"status": "not_found", "message": "..."}
    {"status": "already_synced", "snapshot_path": "..."}
    {"status": "error", "message": "..."}
"""

import argparse
import fcntl
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

SNAPSHOT_NAMES = ["snapshot.json"]
IMPLEMENTATION_SNAPSHOT = "implementation/snapshot.json"


def find_nearest_snapshot(cwd: Path) -> Path | None:
    """Search upward from cwd for snapshot.json, up to 4 levels."""
    search_dir = cwd
    for _ in range(4):
        for rel in SNAPSHOT_NAMES + [IMPLEMENTATION_SNAPSHOT]:
            candidate = search_dir / rel
            if candidate.is_file():
                return candidate
        parent = search_dir.parent
        if parent == search_dir:
            break
        search_dir = parent
    return None


def sync_session(snapshot_path: Path, session_id: str) -> dict:
    """Update session_id and updated_at atomically with flock."""
    lock_path = snapshot_path.parent / "snapshot.lock"

    lock_fd = open(lock_path, "w")
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)

        try:
            with open(snapshot_path) as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return {"status": "error", "message": f"Could not read {snapshot_path}"}

        if not isinstance(data, dict):
            return {"status": "error", "message": "Snapshot is not a valid JSON object"}

        if data.get("session_id") == session_id:
            return {
                "status": "already_synced",
                "snapshot_path": str(snapshot_path),
            }

        data["session_id"] = session_id
        data["updated_at"] = datetime.now(timezone.utc).isoformat()

        tmp_path = str(snapshot_path) + ".tmp"
        try:
            with open(tmp_path, "w") as f:
                json.dump(data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, str(snapshot_path))
        except OSError as e:
            return {"status": "error", "message": f"Write failed: {e}"}
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

        return {
            "status": "synced",
            "snapshot_path": str(snapshot_path),
            "session_id": session_id,
        }
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--cwd", default=os.getcwd())
    args = parser.parse_args()

    cwd = Path(args.cwd).resolve()
    snapshot = find_nearest_snapshot(cwd)

    if snapshot is None:
        print(json.dumps({
            "status": "not_found",
            "message": f"No snapshot.json found searching upward from {cwd}",
        }))
        return 1

    result = sync_session(snapshot, args.session_id)
    print(json.dumps(result, indent=2))
    return 0 if result["status"] in ("synced", "already_synced") else 1


if __name__ == "__main__":
    sys.exit(main())
