"""Background worker thread for scanning and duplicate detection."""

from typing import List, Optional

from PySide6.QtCore import QObject, Signal

from .scanner import FileInfo, ScanConfig, scan_files
from .deduper import DuplicateGroup, find_duplicates


class ScanWorker(QObject):
    progress = Signal(str, int, int)
    files_found = Signal(int)
    finished = Signal(list)
    cancelled = Signal()
    error = Signal(str)

    def __init__(self, config: ScanConfig, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.config = config
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            check = lambda: self._cancelled
            self.progress.emit("正在扫描文件...", 0, 0)
            files = scan_files(self.config, progress_callback=self._on_file_scanned,
                               cancel_check=check)
            if self._cancelled:
                self.cancelled.emit()
                return
            self.files_found.emit(len(files))
            if not files:
                self.finished.emit([])
                return

            groups = find_duplicates(files, progress_callback=self._on_hash_progress,
                                     cancel_check=check)
            if self._cancelled:
                self.cancelled.emit()
                return
            self.finished.emit(groups)
        except Exception as e:
            self.error.emit(str(e))

    def _on_file_scanned(self, count: int, _path: str):
        if count % 100 == 0:
            self.progress.emit(f"已扫描 {count} 个文件...", count, 0)

    def _on_hash_progress(self, stage: str, current: int, total: int):
        if current % 20 == 0:
            self.progress.emit(stage, current, total)
