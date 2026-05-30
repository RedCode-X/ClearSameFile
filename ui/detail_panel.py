"""Bottom-right panel: shows files in the selected group with color-coded keep/delete."""

import os
import datetime
from typing import List, Optional, Set

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QCheckBox,
    QPushButton,
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QColor, QBrush, QFont

from core.deduper import DuplicateGroup, select_best_file
from ui.dialogs import format_size


KEEP_COLOR = QColor(220, 255, 220)    # light green
DELETE_COLOR = QColor(255, 220, 220)  # light red
KEEP_TEXT = QColor(34, 139, 34)       # green
DELETE_TEXT = QColor(200, 50, 50)     # red


class DetailPanel(QWidget):
    """Shows files of the selected duplicate group with keep/delete toggles."""

    deletion_changed = Signal()  # emitted when any toggle changes

    def __init__(self, parent=None):
        super().__init__(parent)
        self._group: Optional[DuplicateGroup] = None
        self._suppress = False
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Header
        hdr = QHBoxLayout()
        self.group_label = QLabel("选中组详情 — 点击某组查看文件")
        self.group_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        hdr.addWidget(self.group_label)
        hdr.addStretch()

        self.keep_all_btn = QPushButton("全部保留")
        self.keep_all_btn.setToolTip("该组所有文件都不删除")
        self.keep_all_btn.clicked.connect(lambda: self._set_all(False))
        self.keep_all_btn.setVisible(False)

        self.delete_all_btn = QPushButton("全部标记删除")
        self.delete_all_btn.setToolTip("标记该组所有文件为删除（危险：至少保留一个）")
        self.delete_all_btn.clicked.connect(lambda: self._set_all(True))
        self.delete_all_btn.setVisible(False)

        hdr.addWidget(self.keep_all_btn)
        hdr.addWidget(self.delete_all_btn)
        layout.addLayout(hdr)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["删除", "状态", "文件名", "路径", "大小", "修改日期"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(False)
        self.table.verticalHeader().setVisible(False)

        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 40)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(1, 50)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(2, 180)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(4, 80)
        hh.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(5, 130)

        self.table.cellDoubleClicked.connect(self._on_double_click)
        layout.addWidget(self.table)

    def set_group(self, group: Optional[DuplicateGroup], checked_files: Optional[Set[str]] = None):
        self._suppress = True
        self._group = group
        self.table.setRowCount(0)

        if group is None:
            self.group_label.setText("选中组详情 — 点击某组查看文件")
            self.keep_all_btn.setVisible(False)
            self.delete_all_btn.setVisible(False)
            self._suppress = False
            return

        self.group_label.setText(
            f"组详情 — {len(group.files)} 个重复, "
            f"可释放 {format_size(group.wasted_size)}"
        )
        self.keep_all_btn.setVisible(True)
        self.delete_all_btn.setVisible(True)

        sorted_files = sorted(group.files, key=lambda f: f.path)
        checked = checked_files or set()

        self.table.setRowCount(len(sorted_files))
        for row, fi in enumerate(sorted_files):
            is_delete = fi.path in checked
            self._set_row(row, fi, is_delete)

        self._suppress = False

    def _set_row(self, row: int, fi, is_delete: bool = False):
        # Checkbox
        cb = QCheckBox()
        cb.setChecked(is_delete)
        cb.stateChanged.connect(lambda state, r=row: self._on_toggle(r, state))
        container = QWidget()
        cl = QHBoxLayout(container)
        cl.addWidget(cb)
        cl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cl.setContentsMargins(0, 0, 0, 0)
        self.table.setCellWidget(row, 0, container)

        # Status label
        status = "删除" if is_delete else "保留"
        status_item = QTableWidgetItem(status)
        status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        bold_font = QFont()
        bold_font.setBold(True)
        status_item.setFont(bold_font)
        self.table.setItem(row, 1, status_item)

        # Filename
        self.table.setItem(row, 2, QTableWidgetItem(fi.name))

        # Path
        self.table.setItem(row, 3, QTableWidgetItem(fi.dir))

        # Size
        size_item = QTableWidgetItem(format_size(fi.size))
        size_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.table.setItem(row, 4, size_item)

        # Date
        dt = datetime.datetime.fromtimestamp(fi.mtime)
        self.table.setItem(row, 5, QTableWidgetItem(dt.strftime("%Y-%m-%d %H:%M")))

        self.table.setRowHeight(row, 28)
        self._color_row(row, is_delete)

    def _color_row(self, row: int, is_delete: bool):
        bg = DELETE_COLOR if is_delete else KEEP_COLOR
        text_color = DELETE_TEXT if is_delete else KEEP_TEXT
        for col in range(self.table.columnCount()):
            item = self.table.item(row, col)
            if item:
                item.setBackground(QBrush(bg))
                item.setForeground(QBrush(text_color))

    def _on_toggle(self, row: int, state: int):
        if self._suppress:
            return
        is_delete = state == Qt.CheckState.Checked.value
        self.table.item(row, 1).setText("删除" if is_delete else "保留")
        self._color_row(row, is_delete)
        self.deletion_changed.emit()

    def _set_all(self, delete_all: bool):
        if self._group is None:
            return
        self._suppress = True
        total = self.table.rowCount()
        for row in range(total):
            if delete_all and row == total - 1:
                # Keep at least one file
                cb = self.table.cellWidget(row, 0).findChild(QCheckBox)
                cb.setChecked(False)
                self.table.item(row, 1).setText("保留")
                self._color_row(row, False)
                continue
            # If delete_all and this is NOT the last row, check it
            # If not delete_all (keep all), uncheck everything
            cb = self.table.cellWidget(row, 0).findChild(QCheckBox)
            # For "delete all except last": check all rows except last
            # For "keep all": uncheck all rows
            should_delete = delete_all and (row < total - 1 or total == 1)
            cb.setChecked(should_delete)
            self.table.item(row, 1).setText("删除" if should_delete else "保留")
            self._color_row(row, should_delete)
        self._suppress = False
        self.deletion_changed.emit()

    def _on_double_click(self, row: int, col: int):
        if col <= 1:
            return
        if self._group:
            sorted_files = sorted(self._group.files, key=lambda f: f.path)
            if row < len(sorted_files):
                try:
                    os.startfile(sorted_files[row].path)
                except OSError:
                    pass

    def get_selected_files(self) -> List[str]:
        """Return file paths marked for deletion."""
        if self._group is None:
            return []
        sorted_files = sorted(self._group.files, key=lambda f: f.path)
        result = []
        for row in range(min(self.table.rowCount(), len(sorted_files))):
            cb = self.table.cellWidget(row, 0).findChild(QCheckBox)
            if cb and cb.isChecked():
                result.append(sorted_files[row].path)
        return result

    def apply_strategy(self, strategy: str):
        """Apply selection strategy. Returns set of file paths to delete."""
        if self._group is None or len(self._group.files) < 2:
            return

        sorted_files = sorted(self._group.files, key=lambda f: f.path)
        keep_idx = select_best_file(sorted_files, strategy)
        if keep_idx < 0:
            return

        self._suppress = True
        for row in range(self.table.rowCount()):
            is_delete = (row != keep_idx)
            cb = self.table.cellWidget(row, 0).findChild(QCheckBox)
            if cb:
                cb.setChecked(is_delete)
                self.table.item(row, 1).setText("删除" if is_delete else "保留")
                self._color_row(row, is_delete)
        self._suppress = False
        self.deletion_changed.emit()
