"""Right-top panel: duplicate groups table with global strategy, delete summary."""

from typing import List, Dict, Set, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QPushButton, QLabel, QComboBox,
)
from PySide6.QtCore import Signal, Qt

from core.deduper import DuplicateGroup
from ui.dialogs import format_size


class ResultPanel(QWidget):
    """Displays duplicate groups with a global selection strategy."""

    group_selected = Signal(int)                     # row clicked → show details
    strategy_changed = Signal(str)                   # 'keep_newest' etc.
    delete_requested = Signal()                      # user clicked execute delete
    preview_requested = Signal()                     # user wants to see delete list
    export_requested = Signal()                      # export CSV

    STRATEGIES = {
        "keep_smart": "智能保留",
        "keep_newest": "保留最新",
        "keep_oldest": "保留最旧",
        "keep_shortest_path": "保留最短路径",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._groups: List[DuplicateGroup] = []
        self._checked_count = 0      # total files marked for deletion
        self._checked_size = 0
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        # Title + Strategy row
        top = QHBoxLayout()
        title = QLabel("重复文件列表")
        title.setStyleSheet("font-weight: bold; font-size: 13px;")
        top.addWidget(title)
        top.addStretch()

        top.addWidget(QLabel("策略:"))
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems(self.STRATEGIES.values())
        self.strategy_combo.setCurrentIndex(0)  # keep_newest
        self.strategy_combo.setMinimumWidth(140)
        self.strategy_combo.setEnabled(False)
        self.strategy_combo.currentIndexChanged.connect(self._on_strategy_changed)
        top.addWidget(self.strategy_combo)

        layout.addLayout(top)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["组号", "文件数", "单文件大小", "可释放空间", "待删", "示例文件"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(True)

        hh = self.table.horizontalHeader()
        for i, w in enumerate([50, 60, 95, 105, 50, 200]):
            hh.setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed if i < 5 else QHeaderView.ResizeMode.Stretch)
            self.table.setColumnWidth(i, w)

        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.table)

        # Summary + Actions
        bottom = QVBoxLayout()
        bottom.setSpacing(4)

        self.summary_label = QLabel("")
        self.summary_label.setStyleSheet("color: #666; font-size: 12px; padding: 4px 0;")
        bottom.addWidget(self.summary_label)

        btn_row = QHBoxLayout()

        self.preview_btn = QPushButton("预览删除列表")
        self.preview_btn.setEnabled(False)
        self.preview_btn.clicked.connect(lambda: self.preview_requested.emit())

        self.reset_btn = QPushButton("全部重置")
        self.reset_btn.setEnabled(False)
        self.reset_btn.clicked.connect(lambda: self.strategy_changed.emit("reset"))

        self.export_btn = QPushButton("导出 CSV")
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(lambda: self.export_requested.emit())

        self.delete_btn = QPushButton("执行删除")
        self.delete_btn.setEnabled(False)
        self.delete_btn.setMinimumHeight(34)
        self.delete_btn.setMinimumWidth(110)
        self.delete_btn.setStyleSheet(
            "QPushButton { background-color: #d9534f; color: white; font-weight: bold; border-radius: 4px; padding: 6px 16px; }"
            "QPushButton:hover { background-color: #c9302c; }"
            "QPushButton:disabled { background-color: #ccc; color: #888; }"
        )
        self.delete_btn.clicked.connect(lambda: self.delete_requested.emit())

        btn_row.addWidget(self.preview_btn)
        btn_row.addWidget(self.reset_btn)
        btn_row.addWidget(self.export_btn)
        btn_row.addStretch()
        btn_row.addWidget(self.delete_btn)
        bottom.addLayout(btn_row)

        layout.addLayout(bottom)

    def set_groups(self, groups: List[DuplicateGroup]):
        self._groups = groups
        self.table.setRowCount(len(groups))

        has_groups = len(groups) > 0
        self.strategy_combo.setEnabled(has_groups)
        self.export_btn.setEnabled(has_groups)
        self.reset_btn.setEnabled(has_groups)

        if not groups:
            self._update_summary()
            return

        for i, g in enumerate(groups):
            self.table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.table.setItem(i, 1, QTableWidgetItem(str(len(g.files))))

            size_item = QTableWidgetItem(format_size(g.files[0].size))
            size_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(i, 2, size_item)

            wasted_item = QTableWidgetItem(format_size(g.wasted_size))
            wasted_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(i, 3, wasted_item)

            # Placeholder for "待删" count - will be updated by main window
            self.table.setItem(i, 4, QTableWidgetItem("0"))
            self.table.item(i, 4).setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            sample = g.files[0].name if g.files else ""
            self.table.setItem(i, 5, QTableWidgetItem(sample))
            self.table.setRowHeight(i, 30)

        if self.table.rowCount() > 0:
            self.table.selectRow(0)

        self._update_summary()

    def update_delete_counts(self, row_counts: Dict[int, int]):
        """Update the '待删' column for each group row.
        row_counts: {group_index: count_of_files_marked_for_deletion}
        """
        total = 0
        total_size = 0
        for i in range(min(self.table.rowCount(), len(self._groups))):
            count = row_counts.get(i, 0)
            self.table.item(i, 4).setText(str(count))
            if count > 0 and i < len(self._groups):
                total += count
                total_size += self._groups[i].files[0].size * count if self._groups[i].files else 0

        self._checked_count = total
        self._checked_size = total_size
        self._update_summary()

    def _update_summary(self):
        if self._checked_count > 0:
            self.summary_label.setText(
                f"已标记删除: <b>{self._checked_count}</b> 个文件, "
                f"共 <b>{format_size(self._checked_size)}</b>"
            )
            self.summary_label.setStyleSheet("color: #d9534f; font-size: 12px; padding: 4px 0;")
        else:
            self.summary_label.setText("未标记任何文件。选择一个策略开始筛选。")
            self.summary_label.setStyleSheet("color: #888; font-size: 12px; padding: 4px 0;")

        self.delete_btn.setEnabled(self._checked_count > 0)
        self.preview_btn.setEnabled(self._checked_count > 0)

    def _on_strategy_changed(self, index: int):
        keys = list(self.STRATEGIES.keys())
        if 0 <= index < len(keys):
            self.strategy_changed.emit(keys[index])

    def _on_selection_changed(self):
        rows = set(item.row() for item in self.table.selectedItems())
        if len(rows) == 1:
            self.group_selected.emit(rows.pop())

    def get_groups(self) -> List[DuplicateGroup]:
        return self._groups

    def get_current_strategy(self) -> str:
        keys = list(self.STRATEGIES.keys())
        idx = self.strategy_combo.currentIndex()
        return keys[idx] if 0 <= idx < len(keys) else "keep_newest"

    def set_delete_enabled(self, enabled: bool):
        self.delete_btn.setEnabled(enabled)

    def get_checked_info(self) -> tuple:
        """Return (file_count, total_size) for all checked files."""
        return self._checked_count, self._checked_size
