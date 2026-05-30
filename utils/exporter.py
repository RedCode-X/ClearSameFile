"""Export duplicate report to CSV."""

import csv
import os
from typing import List

from core.deduper import DuplicateGroup


def export_csv(groups: List[DuplicateGroup], filepath: str) -> None:
    """Export duplicate groups to a CSV file."""
    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["组号", "文件数量", "单文件大小(字节)", "可释放空间(字节)", "文件路径"])
        for i, g in enumerate(groups, 1):
            for fi in g.files:
                w.writerow([i, len(g.files), g.files[0].size, g.wasted_size, fi.path])
