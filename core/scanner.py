"""File scanner: walks directory trees and collects file metadata."""

import os
from dataclasses import dataclass, field
from typing import List, Set, Callable, Optional


@dataclass
class FileInfo:
    path: str
    size: int
    mtime: float

    @property
    def name(self) -> str:
        return os.path.basename(self.path)

    @property
    def dir(self) -> str:
        return os.path.dirname(self.path)


@dataclass
class ScanConfig:
    directories: List[str] = field(default_factory=list)
    exclude_dirs: Set[str] = field(default_factory=lambda: {"node_modules", ".git", "__pycache__"})
    min_size: int = 0          # bytes, 0 = no filter
    max_size: int = 0          # bytes, 0 = no filter
    extensions: Set[str] = field(default_factory=set)  # e.g. {".jpg", ".png"}, empty = all


def scan_files(
    config: ScanConfig,
    progress_callback: Optional[Callable[[int, str], None]] = None,
    cancel_check: Optional[Callable[[], bool]] = None,
) -> List[FileInfo]:
    """Walk configured directories and return list of FileInfo objects.

    Args:
        config: ScanConfig with directories, filters.
        progress_callback: Optional callable(count, current_path) for UI progress.
        cancel_check: Optional callable() -> bool, if returns True scanning aborts.

    Returns:
        List of FileInfo for all matching files (partial if cancelled).
    """
    files: List[FileInfo] = []
    count = 0

    for directory in config.directories:
        if not os.path.isdir(directory):
            continue
        for root, dirs, filenames in os.walk(directory):
            dirs[:] = [d for d in dirs if d not in config.exclude_dirs]

            for name in filenames:
                if cancel_check and cancel_check():
                    return files

                filepath = os.path.join(root, name)
                try:
                    stat = os.stat(filepath)
                except OSError:
                    continue

                size = stat.st_size
                if config.min_size > 0 and size < config.min_size:
                    continue
                if config.max_size > 0 and size > config.max_size:
                    continue

                if config.extensions:
                    ext = os.path.splitext(name)[1].lower()
                    if ext not in config.extensions:
                        continue

                files.append(FileInfo(
                    path=filepath,
                    size=size,
                    mtime=stat.st_mtime,
                ))
                count += 1
                if progress_callback:
                    progress_callback(count, filepath)

    return files
