"""Backup manager: safe-delete files to a backup directory with restore capability."""

import os
import json
import shutil
import time
from datetime import datetime
from typing import List, Dict, Optional


BACKUP_ROOT = os.path.join(os.path.expanduser("~"), "ClearSameFile_Backup")


def _ensure_backup_root() -> str:
    os.makedirs(BACKUP_ROOT, exist_ok=True)
    return BACKUP_ROOT


def _session_dir() -> str:
    """Create a timestamped session directory for this batch of deletions."""
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    d = os.path.join(_ensure_backup_root(), ts)
    os.makedirs(d, exist_ok=True)
    return d


def backup_files(filepaths: List[str]) -> Dict[str, list]:
    """Move files to a backup session directory. Returns session info.

    Each file is moved to: BACKUP_ROOT/<timestamp>/<original-drive>/<relative-path>

    Returns dict with keys: session_dir, files (list of {original, backup, size, mtime}).
    """
    session = _session_dir()
    manifest: List[dict] = []
    failed: List[str] = []
    total_size = 0

    for fp in filepaths:
        if not os.path.isfile(fp):
            failed.append(fp)
            continue
        try:
            # Preserve directory structure: C:/Users/X/Docs/file.txt → session/C/Users/X/Docs/file.txt
            # Use the path without the drive colon for valid dir names
            drive = os.path.splitdrive(fp)[0].rstrip(":")  # "C"
            rel = os.path.relpath(fp, os.path.splitdrive(fp)[0] + os.sep) if os.path.splitdrive(fp)[0] else fp
            dest = os.path.join(session, drive, rel)
            os.makedirs(os.path.dirname(dest), exist_ok=True)

            stat = os.stat(fp)
            shutil.move(fp, dest)

            manifest.append({
                "original": fp,
                "backup": dest,
                "size": stat.st_size,
                "mtime": stat.st_mtime,
            })
            total_size += stat.st_size
        except OSError:
            failed.append(fp)

    # Write manifest
    manifest_path = os.path.join(session, "manifest.json")
    meta = {
        "deleted_at": datetime.now().isoformat(),
        "total_files": len(manifest),
        "total_size": total_size,
        "files": manifest,
        "failed": failed,
    }
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    return {"session_dir": session, **meta}


def get_backup_sessions() -> List[dict]:
    """Return list of all backup sessions, newest first."""
    root = _ensure_backup_root()
    sessions = []
    for name in sorted(os.listdir(root), reverse=True):
        session_dir = os.path.join(root, name)
        manifest_path = os.path.join(session_dir, "manifest.json")
        if os.path.isfile(manifest_path):
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                meta["session_dir"] = session_dir
                meta["session_name"] = name
                sessions.append(meta)
            except (json.JSONDecodeError, OSError):
                pass
    return sessions


def get_session_files(session_dir: str) -> List[dict]:
    """Return list of backed-up files in a session, with existence check."""
    manifest_path = os.path.join(session_dir, "manifest.json")
    if not os.path.isfile(manifest_path):
        return []
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
    except (json.JSONDecodeError, OSError):
        return []

    files = meta.get("files", [])
    for entry in files:
        entry["exists"] = os.path.isfile(entry.get("backup", ""))
    return files


def restore_files(entries: List[dict]) -> Dict[str, int]:
    """Restore files from backup to their original locations.

    Args:
        entries: List of dicts with 'backup' and 'original' keys.

    Returns:
        {"success": N, "failed": N, "skipped": N}
    """
    success = 0
    failed = 0
    skipped = 0

    for entry in entries:
        src = entry["backup"]
        dst = entry["original"]
        if not os.path.isfile(src):
            failed += 1
            continue
        if os.path.exists(dst):
            skipped += 1
            continue
        try:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.move(src, dst)
            success += 1
        except OSError:
            failed += 1

    return {"success": success, "failed": failed, "skipped": skipped}


def delete_backup_session(session_dir: str) -> bool:
    """Delete an entire backup session directory permanently."""
    try:
        shutil.rmtree(session_dir)
        return True
    except OSError:
        return False


def clean_empty_sessions() -> int:
    """Remove backup sessions that have no remaining files. Returns count removed."""
    count = 0
    sessions = get_backup_sessions()
    for s in sessions:
        files = get_session_files(s["session_dir"])
        if not files or all(not f.get("exists") for f in files):
            if delete_backup_session(s["session_dir"]):
                count += 1
    return count
