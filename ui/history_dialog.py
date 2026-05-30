"""Scan history dialog: view past scan results and re-load directories."""

from typing import List

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QPushButton, QLabel, QMessageBox,
)
from PySide6.QtCore import Qt, Signal

from utils.config import load_history, save_history_entry
from ui.dialogs import format_size


class HistoryDialog(QDialog):
    """Shows past scan sessions and allows re-scanning their directories."""

    reload_requested = Signal(list)  # List[str] directories

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("扫描历史记录")
        self.setMinimumSize(750, 420)
        self._history: List[dict] = []
        self._build_ui()
        self._load()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("以下为历次扫描结果，选中一行可重新加载其扫描目录。"))

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "时间", "重复组数", "多余文件数", "可释放空间", "扫描目录数", "目录"
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)

        hh = self.table.horizontalHeader()
        for i, w in enumerate([155, 80, 80, 100, 80, 300]):
            hh.setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed if i < 5 else QHeaderView.ResizeMode.Stretch)
            self.table.setColumnWidth(i, w)

        layout.addWidget(self.table)

        # Buttons
        btn_row = QHBoxLayout()
        self.reload_btn = QPushButton("重新加载目录")
        self.reload_btn.setToolTip("将选中记录的扫描目录加载到主界面")
        self.reload_btn.clicked.connect(self._reload_selected)
        self.reload_btn.setEnabled(False)

        self.clear_btn = QPushButton("清空历史")
        self.clear_btn.clicked.connect(self._clear_history)

        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.close)

        btn_row.addWidget(self.reload_btn)
        btn_row.addWidget(self.clear_btn)
        btn_row.addStretch()
        btn_row.addWidget(self.close_btn)
        layout.addLayout(btn_row)

        self.table.itemSelectionChanged.connect(
            lambda: self.reload_btn.setEnabled(len(self.table.selectedItems()) > 0)
        )

    def _load(self):
        self._history = load_history()
        self.table.setRowCount(len(self._history))
        for row, entry in enumerate(self._history):
            time_str = entry.get("time", "")
            # Truncate to readable format
            if len(time_str) > 19:
                time_str = time_str[:19].replace("T", " ")

            self.table.setItem(row, 0, QTableWidgetItem(time_str))
            self.table.setItem(row, 1, QTableWidgetItem(str(entry.get("groups", 0))))

            dup_count = entry.get("duplicate_files", 0)
            item = QTableWidgetItem(str(dup_count))
            item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 2, item)

            wasted = entry.get("wasted_size", 0)
            wasted_item = QTableWidgetItem(format_size(wasted))
            wasted_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 3, wasted_item)

            dirs = entry.get("directories", [])
            self.table.setItem(row, 4, QTableWidgetItem(str(len(dirs))))

            dirs_text = "; ".join(dirs) if dirs else "—"
            self.table.setItem(row, 5, QTableWidgetItem(dirs_text))

            self.table.setRowHeight(row, 26)

    def _reload_selected(self):
        rows = set(item.row() for item in self.table.selectedItems())
        if not rows:
            return
        row = rows.pop()
        if row < len(self._history):
            dirs = self._history[row].get("directories", [])
            if dirs:
                self.reload_requested.emit(dirs)
                self.close()
            else:
                QMessageBox.information(self, "提示", "该记录没有保存扫描目录信息。")

    def _clear_history(self):
        reply = QMessageBox.question(
            self, "确认",
            "确定要清空所有历史记录吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            from utils.config import save_config, load_config
            cfg = load_config()
            cfg["history"] = []
            save_config(cfg)
            self._history = []
            self.table.setRowCount(0)
            self.reload_btn.setEnabled(False)
