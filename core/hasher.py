"""File hashing: fast MD5 partial hash for pre-screening, SHA256 for confirmation."""

import hashlib
from typing import Tuple

PARTIAL_SIZE = 4096  # read first 4 KB for quick screening


def partial_hash(filepath: str) -> str:
    """Compute MD5 of the first PARTIAL_SIZE bytes. Used for quick pre-screening."""
    h = hashlib.md5()
    try:
        with open(filepath, "rb") as f:
            h.update(f.read(PARTIAL_SIZE))
    except OSError:
        return ""
    return h.hexdigest()


def full_hash(filepath: str) -> str:
    """Compute SHA256 of the entire file. Used for exact duplicate confirmation."""
    h = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
    except OSError:
        return ""
    return h.hexdigest()


def quick_hash_pair(filepath: str) -> Tuple[str, str]:
    """Return (partial_md5, full_sha256) for a file. Empty strings on error."""
    partial = hashlib.md5()
    full = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            partial.update(f.read(PARTIAL_SIZE))
            f.seek(0)
            for chunk in iter(lambda: f.read(65536), b""):
                full.update(chunk)
    except OSError:
        return ("", "")
    return (partial.hexdigest(), full.hexdigest())
