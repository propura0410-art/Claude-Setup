#!/usr/bin/env python3
"""Discover active deep-trilogy sessions for /deep-resume.

Searches CWD and parent directories for snapshot files and plugin config files,
determines which plugin was active and what step to resume from.

Output: JSON to stdout with session discovery results.

Possible output shapes:
  {"status": "found", "source": "snapshot", "plugin": "deep-implement", ...}
  {"status": "found", "source": "artifact-scan", "plugin": "deep-plan", ...}
  {"status": "multiple", "sessions": [...]}
  {"status": "not_found", "searched": [...]}

Usage:
    uv run --project {plugin_root}/deep-plan \
        {plugin_root}/scripts/tools/discover-session.py [--cwd PATH]
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SNAPSHOT_VERSION = 1

CONFIG_FILES = {
    "deep_plan_config.json": "deep-plan",
    "deep_implement_config.json": "deep-implement",
    "deep_project_session.json": "deep-project",
}


# ---------------------------------------------------------------------------
# Snapshot helpers (inlined from deep-plan/scripts/lib/snapshot.py)
# ---------------------------------------------------------------------------


def read_snapshot(path: str) -> dict | None:
    """Read and parse snapshot.json. Returns None if missing or corrupt."""
    try:
        with open(path) as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def validate_snapshot(snapshot: dict, working_dir: str) -> bool:
    """Check snapshot version and artifact freshness."""
    if snapshot.get("version") != SNAPSHOT_VERSION:
        return False

    artifacts = snapshot.get("completed_artifacts", [])
    if not artifacts:
        return True

    try:
        updated_at = datetime.fromisoformat(snapshot["updated_at"])
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)
    except (KeyError, ValueError):
        return False

    for rel_path in artifacts:
        if ".." in Path(rel_path).parts or os.path.isabs(rel_path):
            continue
        full_path = os.path.join(working_dir, rel_path)
        if not os.path.exists(full_path):
            return False
        mtime = os.path.getmtime(full_path)
        file_time = datetime.fromtimestamp(mtime, tz=timezone.utc)
        if file_time > updated_at:
            return False

    return True


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


def discover_configs(cwd: Path) -> list[dict]:
    """Search CWD + 3 parent levels AND subdirectories for config/snapshot files.

    Two search strategies:
    1. Upward: CWD → parent → grandparent → great-grandparent (4 levels)
    2. Downward: CWD subdirectories up to 4 levels deep

    Depth encoding:
    - Upward results use depth 0-3 (closer to CWD = lower)
    - Downward results use depth 10+ (always sorted after upward matches at same dir)
    """
    results = []
    seen_paths: set[str] = set()

    # --- Upward search (original behavior) ---
    search_dir = cwd
    for depth in range(4):
        _check_dir_for_artifacts(search_dir, depth, results, seen_paths)

        parent = search_dir.parent
        if parent == search_dir:
            break
        search_dir = parent

    # --- Downward search (find nested planning directories) ---
    _search_downward(cwd, results, seen_paths)

    return results


def _check_dir_for_artifacts(
    directory: Path, depth: int, results: list[dict], seen: set[str]
) -> None:
    """Check a single directory for snapshot.json and config files."""
    for snapshot_rel in ("snapshot.json", "implementation/snapshot.json"):
        snapshot_path = directory / snapshot_rel
        if snapshot_path.is_file():
            key = str(snapshot_path.resolve())
            if key not in seen:
                seen.add(key)
                results.append({
                    "type": "snapshot",
                    "path": str(snapshot_path),
                    "depth": depth,
                })

    for config_name, plugin in CONFIG_FILES.items():
        for config_rel in (config_name, f"implementation/{config_name}"):
            config_path = directory / config_rel
            if config_path.is_file():
                key = str(config_path.resolve())
                if key not in seen:
                    seen.add(key)
                    results.append({
                        "type": "config",
                        "plugin": plugin,
                        "path": str(config_path),
                        "depth": depth,
                    })


def _search_downward(cwd: Path, results: list[dict], seen: set[str]) -> None:
    """Search subdirectories up to 4 levels deep for session artifacts.

    Uses os.walk with depth limiting for efficiency. Skips hidden dirs,
    node_modules, and other non-planning directories.
    """
    skip_dirs = {
        ".git", ".claude", "node_modules", "__pycache__", ".venv",
        "venv", ".tox", ".mypy_cache", ".pytest_cache", "dist", "build",
    }

    target_files = {"snapshot.json"} | set(CONFIG_FILES.keys())

    for dirpath, dirnames, filenames in os.walk(cwd):
        rel = Path(dirpath).relative_to(cwd)
        depth = len(rel.parts)

        # Limit depth
        if depth > 4:
            dirnames.clear()
            continue

        # Skip irrelevant directories
        dirnames[:] = [
            d for d in dirnames
            if d not in skip_dirs and not d.startswith(".")
        ]

        # Check for target files
        for fname in filenames:
            if fname not in target_files:
                continue

            fpath = Path(dirpath) / fname
            key = str(fpath.resolve())
            if key in seen:
                continue
            seen.add(key)

            # Use depth 10+ so upward matches at CWD level (depth 0) always win
            effective_depth = 10 + depth

            if fname == "snapshot.json":
                results.append({
                    "type": "snapshot",
                    "path": str(fpath),
                    "depth": effective_depth,
                })
            elif fname in CONFIG_FILES:
                results.append({
                    "type": "config",
                    "plugin": CONFIG_FILES[fname],
                    "path": str(fpath),
                    "depth": effective_depth,
                })


# ---------------------------------------------------------------------------
# Snapshot resume (fast path)
# ---------------------------------------------------------------------------


def try_snapshot_resume(snapshot_path: str) -> dict | None:
    """Try to build resume info from a snapshot file."""
    snapshot = read_snapshot(snapshot_path)
    if snapshot is None:
        return None

    working_dir = str(Path(snapshot_path).parent)
    valid = validate_snapshot(snapshot, working_dir)

    plugin = snapshot.get("plugin", "")
    if plugin not in ("deep-plan", "deep-implement", "deep-project"):
        return None

    # Build progress string
    task = snapshot.get("task_summary") or {}
    section = snapshot.get("section_progress")
    progress_parts = []
    if task.get("total"):
        progress_parts.append(f"{task.get('completed', 0)}/{task['total']} tasks")
    if section and section.get("total"):
        progress_parts.append(
            f"{section.get('completed', 0)}/{section['total']} sections"
        )

    # Detect completion from snapshot data
    resume_step = snapshot.get("resume_step", 0)
    resume_step_name = snapshot.get("resume_step_name", "")
    complete = _is_session_complete(plugin, resume_step, resume_step_name, working_dir)

    result = {
        "status": "found",
        "source": "snapshot",
        "snapshot_valid": valid,
        "plugin": plugin,
        "resume_step": resume_step,
        "resume_step_name": resume_step_name,
        "progress": ", ".join(progress_parts) if progress_parts else "unknown",
        "git_branch": snapshot.get("git_branch", ""),
        "working_dir": working_dir,
        "snapshot_path": snapshot_path,
        "complete": complete,
    }

    # Add plugin-specific paths from sibling config if available
    _enrich_from_config(result, working_dir, plugin)

    return result


def _is_session_complete(plugin: str, step: int, step_name: str, working_dir: str) -> bool:
    """Detect whether a session is complete based on snapshot state.

    Uses plugin-specific final step numbers and artifact checks.
    """
    # Check for explicit "complete" in step name
    name_lower = step_name.lower()
    if "complete" in name_lower and ("planning" in name_lower or "sections" in name_lower):
        # For deep-plan, verify sections actually exist
        if plugin == "deep-plan":
            sections_dir = Path(working_dir) / "sections"
            if sections_dir.is_dir():
                section_files = list(sections_dir.glob("section-*.md"))
                index_exists = (sections_dir / "index.md").exists()
                if section_files and index_exists:
                    return True
        return step >= 20  # Fallback: step 20+ with "complete" in name

    # deep-plan final steps: 21 (final verification) or 22 (output summary)
    if plugin == "deep-plan" and step >= 21:
        return True

    # deep-implement: check if all sections are done
    if plugin == "deep-implement" and "all sections" in name_lower:
        return True

    # deep-project: check if all specs are written
    if plugin == "deep-project" and "all specs" in name_lower:
        return True

    return False


def _enrich_from_config(result: dict, working_dir: str, plugin: str) -> None:
    """Add sections_dir/target_dir etc. from the config file next to the snapshot."""
    config_map = {
        "deep-plan": "deep_plan_config.json",
        "deep-implement": "deep_implement_config.json",
        "deep-project": "deep_project_session.json",
    }
    config_name = config_map.get(plugin)
    if not config_name:
        return

    config_path = os.path.join(working_dir, config_name)
    try:
        with open(config_path) as f:
            config = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return

    if plugin == "deep-implement":
        result["sections_dir"] = config.get("sections_dir", "")
        result["target_dir"] = config.get("target_dir", "")
    elif plugin == "deep-plan":
        result["planning_dir"] = config.get("planning_dir", working_dir)


# ---------------------------------------------------------------------------
# Artifact scanners (fallback path)
# ---------------------------------------------------------------------------


def scan_plan_artifacts(config_path: str) -> dict:
    """Scan deep-plan artifacts to determine resume state.

    Mirrors logic from setup-planning-session.py:scan_planning_files()
    and infer_resume_step().
    """
    planning_dir = str(Path(config_path).parent)
    d = Path(planning_dir)

    files = {
        "research": (d / "claude-research.md").exists(),
        "interview": (d / "claude-interview.md").exists(),
        "spec": (d / "claude-spec.md").exists(),
        "plan": (d / "claude-plan.md").exists(),
        "integration_notes": (d / "claude-integration-notes.md").exists(),
        "plan_tdd": (d / "claude-plan-tdd.md").exists(),
        "reviews": list((d / "reviews").glob("*.md")) if (d / "reviews").exists() else [],
        "sections": list((d / "sections").glob("section-*.md")) if (d / "sections").exists() else [],
        "sections_index": (d / "sections" / "index.md").exists(),
    }

    sections_done = len(files["sections"])

    # Infer resume step — highest artifact wins, with prerequisite checks
    if files["sections_index"]:
        if not files["plan_tdd"]:
            return _plan_result(planning_dir, 16, "missing prerequisite: TDD plan", files, sections_done)
        if sections_done > 0:
            return _plan_result(planning_dir, None, "complete", files, sections_done)
        return _plan_result(planning_dir, 19, "index created, generating sections", files, 0)

    if files["sections"] and not files["sections_index"]:
        if not files["plan_tdd"]:
            return _plan_result(planning_dir, 16, "missing prerequisite: TDD plan", files, sections_done)
        return _plan_result(planning_dir, 18, "section files exist but no index", files, sections_done)

    if files["plan_tdd"]:
        return _plan_result(planning_dir, 17, "TDD plan complete", files, 0)
    if files["integration_notes"]:
        if not files["plan"]:
            return _plan_result(planning_dir, 11, "missing prerequisite: plan", files, 0)
        return _plan_result(planning_dir, 15, "feedback integrated", files, 0)
    if files["reviews"]:
        if not files["plan"]:
            return _plan_result(planning_dir, 11, "missing prerequisite: plan", files, 0)
        return _plan_result(planning_dir, 14, "external review complete", files, 0)
    if files["plan"]:
        if not files["spec"]:
            return _plan_result(planning_dir, 10, "missing prerequisite: spec", files, 0)
        return _plan_result(planning_dir, 12, "plan complete", files, 0)
    if files["spec"]:
        if not files["interview"]:
            return _plan_result(planning_dir, 9, "missing prerequisite: interview", files, 0)
        return _plan_result(planning_dir, 11, "spec complete", files, 0)
    if files["interview"]:
        return _plan_result(planning_dir, 10, "interview complete", files, 0)
    if files["research"]:
        return _plan_result(planning_dir, 8, "research complete", files, 0)

    return _plan_result(planning_dir, 6, "fresh start", files, 0)


def _plan_result(
    planning_dir: str,
    step: int | None,
    description: str,
    files: dict,
    sections_done: int,
) -> dict:
    artifact_count = sum(
        1
        for k in ("research", "interview", "spec", "plan", "integration_notes", "plan_tdd")
        if files.get(k)
    )

    if sections_done > 0:
        progress = f"{sections_done} sections written, {artifact_count}/6 artifacts"
    else:
        progress = f"{artifact_count}/6 artifacts"

    return {
        "status": "found",
        "source": "artifact-scan",
        "plugin": "deep-plan",
        "resume_step": step,
        "resume_step_name": description,
        "progress": progress,
        "git_branch": _get_git_branch(),
        "working_dir": planning_dir,
        "snapshot_path": None,
        "complete": step is None,
    }


def scan_implement_artifacts(config_path: str) -> dict:
    """Scan deep-implement artifacts to determine resume state.

    Mirrors logic from setup_implementation_session.py:infer_session_state()
    and detect_section_review_state().
    """
    try:
        with open(config_path) as f:
            config = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"status": "error", "error": f"Cannot read {config_path}"}

    state_dir = Path(config_path).parent
    sections = config.get("sections", [])
    sections_state = config.get("sections_state", {})

    # Count completed sections (status == "complete" with commit_hash)
    completed = []
    for section in sections:
        s = sections_state.get(section, {})
        if s.get("status") == "complete" and s.get("commit_hash"):
            completed.append(section)

    base = {
        "source": "artifact-scan",
        "plugin": "deep-implement",
        "progress": f"{len(completed)}/{len(sections)} sections",
        "git_branch": _get_git_branch(),
        "working_dir": str(state_dir),
        "sections_dir": config.get("sections_dir", ""),
        "target_dir": config.get("target_dir", ""),
        "snapshot_path": None,
    }

    if len(completed) >= len(sections) and sections:
        return {
            **base,
            "status": "found",
            "resume_step": None,
            "resume_step_name": "all sections complete",
            "complete": True,
        }

    # Find first incomplete section
    resume_from = None
    for section in sections:
        if section not in completed:
            resume_from = section
            break

    # Detect sub-step within the resume section
    sub_step = "implement"
    if resume_from:
        section_num = resume_from.split("-")[1] if "-" in resume_from else "00"
        cr_dir = state_dir / "code_review"
        if (cr_dir / f"section-{section_num}-interview.md").exists():
            sub_step = "apply_fixes"
        elif (cr_dir / f"section-{section_num}-review.md").exists():
            sub_step = "interview"
        elif (cr_dir / f"section-{section_num}-diff.md").exists():
            sub_step = "review"

    return {
        **base,
        "status": "found",
        "resume_step": "setup-implementation",
        "resume_step_name": f"{resume_from} ({sub_step})" if resume_from else "unknown",
        "complete": False,
        "resume_section": resume_from,
        "resume_sub_step": sub_step,
    }


def scan_project_artifacts(config_path: str) -> dict:
    """Scan deep-project artifacts to determine resume state.

    Mirrors logic from deep-project/scripts/lib/state.py:detect_state().
    """
    project_dir = str(Path(config_path).parent)
    d = Path(project_dir)

    interview_exists = (d / "deep_project_interview.md").exists()
    manifest_exists = (d / "project-manifest.md").exists()

    # Find split directories (NN-name pattern)
    split_pattern = re.compile(r"^\d{2}-[a-z0-9]+(?:-[a-z0-9]+)*$")
    splits = sorted([
        item.name
        for item in d.iterdir()
        if item.is_dir() and split_pattern.match(item.name)
    ])

    splits_with_specs = [s for s in splits if (d / s / "spec.md").exists()]

    # Determine resume step
    if splits and len(splits_with_specs) == len(splits):
        step, desc, complete = 7, "all specs written", True
    elif splits:
        missing = len(splits) - len(splits_with_specs)
        step, desc, complete = 6, f"{missing} specs remaining", False
    elif manifest_exists:
        step, desc, complete = 4, "manifest created, awaiting confirmation", False
    elif interview_exists:
        step, desc, complete = 2, "interview complete", False
    else:
        step, desc, complete = 1, "fresh start", False

    if splits:
        progress = f"{len(splits_with_specs)}/{len(splits)} specs"
    elif manifest_exists:
        progress = "manifest created"
    elif interview_exists:
        progress = "interview done"
    else:
        progress = "not started"

    return {
        "status": "found",
        "source": "artifact-scan",
        "plugin": "deep-project",
        "resume_step": step if not complete else None,
        "resume_step_name": desc,
        "progress": progress,
        "git_branch": _get_git_branch(),
        "working_dir": project_dir,
        "snapshot_path": None,
        "complete": complete,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_git_branch() -> str:
    """Get current git branch name."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return ""


# ---------------------------------------------------------------------------
# Project overview (cross-phase comprehensive scan)
# ---------------------------------------------------------------------------


def parse_manifest(project_dir: Path) -> list[str] | None:
    """Parse split names from project-manifest.md SPLIT_MANIFEST block."""
    manifest_path = project_dir / "project-manifest.md"
    if not manifest_path.exists():
        return None
    try:
        content = manifest_path.read_text()
    except OSError:
        return None
    match = re.search(
        r"<!--\s*SPLIT_MANIFEST\s*\n(.*?)\nEND_MANIFEST\s*-->",
        content,
        re.DOTALL,
    )
    if not match:
        return None
    names = [line.strip() for line in match.group(1).strip().splitlines() if line.strip()]
    return names or None


def find_project_root(cwd: Path) -> Path | None:
    """Search CWD and parents for a project directory with splits."""
    search = cwd
    for _ in range(5):
        if (search / "deep_project_session.json").is_file():
            if parse_manifest(search) is not None:
                return search
            # Fallback: check for split-like directories
            pat = re.compile(r"^\d{2}-[a-z0-9]+(?:-[a-z0-9]+)*$")
            try:
                if any(p.is_dir() and pat.match(p.name) for p in search.iterdir()):
                    return search
            except OSError:
                pass
        parent = search.parent
        if parent == search:
            break
        search = parent
    return None


def build_split_status(name: str, project_dir: Path) -> dict:
    """Build plan and implement status for one split."""
    split_dir = project_dir / name
    result = {"name": name, "split_dir": str(split_dir)}

    if not split_dir.is_dir():
        result.update({
            "exists": False,
            "spec_exists": False,
            "plan": {"status": "blocked", "blocked_reason": "directory not created"},
            "implement": {"status": "blocked", "blocked_reason": "directory not created"},
        })
        return result

    result["exists"] = True
    result["spec_exists"] = (split_dir / "spec.md").exists()

    # --- Plan phase ---
    plan_cfg = split_dir / "deep_plan_config.json"
    if plan_cfg.is_file():
        raw = scan_plan_artifacts(str(plan_cfg))
        sections_dir = split_dir / "sections"
        has_secs = sections_dir.is_dir() and bool(list(sections_dir.glob("section-*.md")))
        result["plan"] = {
            "status": "complete" if raw.get("complete") else "in_progress",
            "progress": raw.get("progress", ""),
            "resume_step": raw.get("resume_step"),
            "resume_step_name": raw.get("resume_step_name", ""),
            "working_dir": raw.get("working_dir", str(split_dir)),
            "has_sections": has_secs,
        }
    elif result["spec_exists"]:
        result["plan"] = {"status": "not_started", "has_sections": False}
    else:
        result["plan"] = {
            "status": "blocked",
            "blocked_reason": "no spec.md",
            "has_sections": False,
        }

    # --- Implement phase ---
    impl_cfg = None
    for rel in ("implementation/deep_implement_config.json", "deep_implement_config.json"):
        p = split_dir / rel
        if p.is_file():
            impl_cfg = p
            break

    if impl_cfg:
        raw = scan_implement_artifacts(str(impl_cfg))
        if raw.get("status") == "error":
            result["implement"] = {"status": "error", "error": raw.get("error", "unknown")}
        else:
            result["implement"] = {
                "status": "complete" if raw.get("complete") else "in_progress",
                "progress": raw.get("progress", ""),
                "resume_step": raw.get("resume_step"),
                "resume_step_name": raw.get("resume_step_name", ""),
                "resume_section": raw.get("resume_section"),
                "resume_sub_step": raw.get("resume_sub_step"),
                "working_dir": raw.get("working_dir", str(impl_cfg.parent)),
                "sections_dir": raw.get("sections_dir", ""),
                "target_dir": raw.get("target_dir", ""),
            }
    else:
        plan_status = result["plan"].get("status", "blocked")
        has_secs = result["plan"].get("has_sections", False)
        if plan_status == "complete" or has_secs:
            result["implement"] = {"status": "not_started"}
        elif plan_status in ("in_progress", "not_started"):
            result["implement"] = {
                "status": "blocked",
                "blocked_reason": "planning not complete",
            }
        else:
            result["implement"] = {
                "status": "blocked",
                "blocked_reason": result["plan"].get("blocked_reason", "planning blocked"),
            }

    return result


def suggest_next_action(splits: list[dict]) -> dict | None:
    """Pick the next action respecting lifecycle ordering.

    Priority order:
      1. In-progress implementation -> resume
      2. In-progress planning -> resume
      3. Completed plan with no implementation -> start implementation
      4. Spec exists but no plan started -> start planning
    """
    # Priority 1: Resume in-progress implementation (earliest split)
    for s in splits:
        impl = s.get("implement", {})
        if impl.get("status") == "in_progress":
            return {
                "action": "resume",
                "plugin": "deep-implement",
                "split": s["name"],
                "description": impl.get("resume_step_name", "unknown"),
                "working_dir": impl.get("working_dir", s.get("split_dir", "")),
            }

    # Priority 2: Resume in-progress planning (earliest split)
    for s in splits:
        plan = s.get("plan", {})
        if plan.get("status") == "in_progress":
            return {
                "action": "resume",
                "plugin": "deep-plan",
                "split": s["name"],
                "description": plan.get("resume_step_name", "unknown"),
                "working_dir": plan.get("working_dir", s.get("split_dir", "")),
            }

    # Priority 3: Completed plan, no implementation started
    for s in splits:
        plan = s.get("plan", {})
        impl = s.get("implement", {})
        if plan.get("status") == "complete" and impl.get("status") == "not_started":
            return {
                "action": "start",
                "plugin": "deep-implement",
                "split": s["name"],
                "description": f"ready to implement ({plan.get('progress', '')})",
                "working_dir": plan.get("working_dir", s.get("split_dir", "")),
            }

    # Priority 4: Spec exists, no plan started
    for s in splits:
        plan = s.get("plan", {})
        if s.get("spec_exists") and plan.get("status") == "not_started":
            return {
                "action": "start",
                "plugin": "deep-plan",
                "split": s["name"],
                "description": "spec available, ready to plan",
                "working_dir": s.get("split_dir", ""),
            }

    return None


def build_project_overview(project_dir: Path) -> dict | None:
    """Comprehensive status across all splits and lifecycle phases."""
    split_names = parse_manifest(project_dir)
    if split_names is None:
        pat = re.compile(r"^\d{2}-[a-z0-9]+(?:-[a-z0-9]+)*$")
        try:
            split_names = sorted(
                p.name for p in project_dir.iterdir()
                if p.is_dir() and pat.match(p.name)
            )
        except OSError:
            return None
    if not split_names:
        return None

    # Project decomposition phase
    sess = project_dir / "deep_project_session.json"
    if sess.is_file():
        proj = scan_project_artifacts(str(sess))
        proj_phase = {
            "complete": proj.get("complete", False),
            "progress": proj.get("progress", ""),
        }
    else:
        proj_phase = {"complete": True, "progress": "session file missing"}

    # Scan each split
    splits = [build_split_status(n, project_dir) for n in split_names]
    suggested = suggest_next_action(splits)

    # Summary counts
    total = len(splits)
    pc = sum(1 for s in splits if s["plan"].get("status") == "complete")
    pi = sum(1 for s in splits if s["plan"].get("status") == "in_progress")
    ic = sum(1 for s in splits if s["implement"].get("status") == "complete")
    ii = sum(1 for s in splits if s["implement"].get("status") == "in_progress")

    return {
        "status": "project_overview",
        "project_dir": str(project_dir),
        "git_branch": _get_git_branch(),
        "project_phase": proj_phase,
        "summary": {
            "total_splits": total,
            "plans_complete": pc,
            "plans_in_progress": pi,
            "implementations_complete": ic,
            "implementations_in_progress": ii,
            "all_done": pc == total and ic == total,
        },
        "splits": splits,
        "suggested_next": suggested,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    """Discover sessions and output JSON."""
    cwd = Path(os.getcwd())

    # Parse --cwd override
    args = sys.argv[1:]
    for i, arg in enumerate(args):
        if arg == "--cwd" and i + 1 < len(args):
            cwd = Path(args[i + 1]).resolve()
            break

    # Step 1: Check for project overview (cross-phase view)
    project_dir = find_project_root(cwd)
    if project_dir is not None:
        overview = build_project_overview(project_dir)
        if overview is not None:
            print(json.dumps(overview, indent=2))
            return 0

    # Step 2: Discover config files and snapshots (single-session fallback)
    discovered = discover_configs(cwd)

    if not discovered:
        print(json.dumps({
            "status": "not_found",
            "searched": [str(cwd)],
            "message": "No deep-trilogy session artifacts found",
        }))
        return 0

    # Step 3: Try snapshots first — prefer most recently updated
    snapshots = sorted(
        [d for d in discovered if d["type"] == "snapshot"],
        key=lambda d: d["depth"],
    )

    # Build valid snapshot results, sorted by recency
    valid_snapshots: list[dict] = []
    for snap in snapshots:
        result = try_snapshot_resume(snap["path"])
        if result is not None:
            # Read updated_at for sorting by recency
            snapshot_data = read_snapshot(snap["path"])
            updated_at = snapshot_data.get("updated_at", "") if snapshot_data else ""
            result["_updated_at"] = updated_at
            valid_snapshots.append(result)

    if valid_snapshots:
        # Sort by updated_at descending (most recent first)
        valid_snapshots.sort(key=lambda r: r.get("_updated_at", ""), reverse=True)

        if len(valid_snapshots) == 1:
            result = valid_snapshots[0]
            result.pop("_updated_at", None)
            print(json.dumps(result, indent=2))
            return 0

        # Multiple valid snapshots — filter out completed sessions, prefer active
        active = [s for s in valid_snapshots if not s.get("complete", False)]
        if len(active) == 1:
            result = active[0]
            result.pop("_updated_at", None)
            print(json.dumps(result, indent=2))
            return 0
        elif len(active) > 1:
            # Multiple active sessions — present as choices
            for s in active:
                s.pop("_updated_at", None)
            print(json.dumps({"status": "multiple", "sessions": active}, indent=2))
            return 0
        else:
            # All complete — return most recent
            result = valid_snapshots[0]
            result.pop("_updated_at", None)
            print(json.dumps(result, indent=2))
            return 0

    # Step 4: Fall back to config-based artifact scanning
    configs = sorted(
        [d for d in discovered if d["type"] == "config"],
        key=lambda d: d["depth"],
    )

    if not configs:
        print(json.dumps({
            "status": "not_found",
            "searched": [str(cwd)],
            "message": "Found snapshot(s) but all were invalid; no config files found",
        }))
        return 0

    # Group by plugin, take closest (lowest depth) for each
    by_plugin: dict[str, dict] = {}
    for cfg in configs:
        plugin = cfg["plugin"]
        if plugin not in by_plugin:
            by_plugin[plugin] = cfg

    # Multiple plugins detected — scan all, return choices
    if len(by_plugin) > 1:
        sessions = []
        for plugin, cfg in by_plugin.items():
            if plugin == "deep-plan":
                sessions.append(scan_plan_artifacts(cfg["path"]))
            elif plugin == "deep-implement":
                sessions.append(scan_implement_artifacts(cfg["path"]))
            elif plugin == "deep-project":
                sessions.append(scan_project_artifacts(cfg["path"]))
        print(json.dumps({"status": "multiple", "sessions": sessions}, indent=2))
        return 0

    # Single plugin — scan its artifacts
    cfg = list(by_plugin.values())[0]
    if cfg["plugin"] == "deep-plan":
        result = scan_plan_artifacts(cfg["path"])
    elif cfg["plugin"] == "deep-implement":
        result = scan_implement_artifacts(cfg["path"])
    elif cfg["plugin"] == "deep-project":
        result = scan_project_artifacts(cfg["path"])
    else:
        result = {"status": "error", "error": f"Unknown plugin: {cfg['plugin']}"}

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
