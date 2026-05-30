"""Duplicate detection: groups files by size, then partial hash, then full hash.
Also provides smart file selection logic for choosing the best copy to keep."""

import os
import re
from collections import defaultdict
from dataclasses import dataclass
from typing import List, Dict, Callable, Optional

from .scanner import FileInfo
from .hasher import partial_hash, full_hash

# --- Smart "best file" selection ---

# Patterns that suggest a file is a copy/derivative, not the original
_COPY_PATTERNS = [
    r'\(\d+\)',             # (1), (2), (123)
    r'\[\d+\]',             # [1], [2]
    r'\bcopy\b',            # copy, Copy
    r'\bcopia\b',           # copia (Spanish/Italian)
    r'\bbackup\b',          # backup
    r'\b副本\b',            # 副本 (Chinese)
    r'\b复件\b',            # 复件 (Chinese)
    r'\bkopia\b',           # kopia (Polish)
    r'-\s*copy\b',          # " - Copy"
    r'_\d+\.',              # _1., _2. before extension
]

# Directories that suggest a file is in a non-original location
_BAD_PATH_TOKENS = [
    'backup', 'temp', 'tmp', 'cache',
    '回收站', 'recycle', '.trash', '$recycle.bin',
    '.stversions',  # Synology versioning
]


def select_best_file(files: List[FileInfo], strategy: str) -> int:
    """Return the index (in the given list) of the best file to keep.

    Args:
        files: List of duplicate FileInfo objects.
        strategy: One of 'keep_newest', 'keep_oldest', 'keep_shortest_path',
                  'keep_smart'.

    Returns:
        Index of the file to keep.
    """
    if len(files) < 2:
        return 0
    return _pick_best(files, strategy)


def _pick_best(files: List[FileInfo], strategy: str) -> int:
    if strategy == 'keep_newest':
        return int(max(range(len(files)), key=lambda i: files[i].mtime))
    elif strategy == 'keep_oldest':
        return int(min(range(len(files)), key=lambda i: files[i].mtime))
    elif strategy == 'keep_shortest_path':
        return int(min(range(len(files)), key=lambda i: len(files[i].path)))
    elif strategy == 'keep_smart':
        return int(min(range(len(files)), key=lambda i: _smart_score(files[i])))
    else:
        return 0


def find_trusted_indices(files: List[FileInfo], trusted_dirs: List[str]) -> List[int]:
    """Return indices of files located inside any trusted directory."""
    result = []
    for i, fi in enumerate(files):
        path_norm = fi.path.replace('\\', '/').lower().rstrip('/')
        for d in trusted_dirs:
            dl = d.replace('\\', '/').lower().rstrip('/')
            if path_norm == dl or path_norm.startswith(dl + '/'):
                result.append(i)
                break
    return result


def _smart_score(fi: FileInfo) -> int:
    """Score a file for 'original-ness'. Lower score = more likely original."""
    name_lower = fi.name.lower()
    path_lower = fi.path.lower()
    score = 0

    # --- Filename penalties ---
    for pat in _COPY_PATTERNS:
        if re.search(pat, name_lower):
            score += 1000

    # Prefer shorter, cleaner names
    score += len(fi.name) * 2

    # --- Path penalties ---
    for token in _BAD_PATH_TOKENS:
        if token in path_lower:
            score += 2000

    # Slight preference for shorter paths
    score += len(fi.path) // 10

    return score


@dataclass
class DuplicateGroup:
    files: List[FileInfo]
    total_size: int = 0
    wasted_size: int = 0

    def __post_init__(self):
        if not self.total_size:
            self.total_size = sum(f.size for f in self.files)
        if not self.wasted_size:
            # space that can be freed = total size minus one copy
            self.wasted_size = self.total_size - self.files[0].size if self.files else 0


def find_duplicates(
    files: List[FileInfo],
    progress_callback: Optional[Callable[[str, int, int], None]] = None,
    cancel_check: Optional[Callable[[], bool]] = None,
) -> List[DuplicateGroup]:
    """Find duplicate files using a three-stage pipeline.

    Stage 1: Group by file size (skip unique sizes).
    Stage 2: Within each size group, group by partial MD5 hash (first 4KB).
    Stage 3: Within each partial-hash group, confirm with full SHA256.

    Args:
        files: List of FileInfo to check.
        progress_callback: Optional callable(stage_name, current, total).
        cancel_check: Optional callable() -> bool, if returns True processing aborts.

    Returns:
        List of DuplicateGroup, each containing 2+ identical files (empty if cancelled).
    """
    # Stage 1: group by size
    by_size: Dict[int, List[FileInfo]] = defaultdict(list)
    for f in files:
        by_size[f.size].append(f)

    # keep only sizes with 2+ files
    candidates = [g for g in by_size.values() if len(g) > 1]
    candidate_count = sum(len(g) for g in candidates)
    if progress_callback:
        progress_callback("阶段1/3: 按文件大小分组", 0, candidate_count)

    # Stage 2: within each size group, compute partial hash
    by_partial: Dict[tuple, List[FileInfo]] = defaultdict(list)
    processed = 0
    for group in candidates:
        if cancel_check and cancel_check():
            return []
        for f in group:
            if cancel_check and cancel_check():
                return []
            ph = partial_hash(f.path)
            if ph:
                by_partial[(f.size, ph)].append(f)
            processed += 1
            if progress_callback and processed % 50 == 0:
                progress_callback("阶段2/3: 计算部分哈希", processed, candidate_count)

    # keep only partial-hash groups with 2+ files
    candidates2 = [g for g in by_partial.values() if len(g) > 1]
    candidate2_count = sum(len(g) for g in candidates2)
    if progress_callback:
        progress_callback("阶段3/3: 计算完整哈希", 0, candidate2_count)

    # Stage 3: full SHA256 confirmation
    by_full: Dict[tuple, List[FileInfo]] = defaultdict(list)
    processed = 0
    for group in candidates2:
        if cancel_check and cancel_check():
            return []
        for f in group:
            if cancel_check and cancel_check():
                return []
            fh = full_hash(f.path)
            if fh:
                by_full[(f.size, fh)].append(f)
            processed += 1
            if progress_callback and processed % 20 == 0:
                progress_callback("阶段3/3: 计算完整哈希", processed, candidate2_count)

    if cancel_check and cancel_check():
        return []

    # build result groups (2+ files with same size and full hash)
    result = []
    for group in by_full.values():
        if len(group) > 1:
            result.append(DuplicateGroup(files=group))

    # sort by wasted_size descending
    result.sort(key=lambda g: g.wasted_size, reverse=True)
    return result
