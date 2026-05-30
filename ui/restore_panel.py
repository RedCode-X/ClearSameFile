"""Restore dialog: browse backup sessions and restore deleted files."""

import os
from typing import List, Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QPushButton, QLabel, QMessageBox,
    QTreeWidget, QTreeWidgetItem, QSplitter, QCheckBox, QWidget,
)
from PySide6.QtCore import Qt, Signal

from core import backup
from ui.dialogs import format_size


class RestoreDialog(QDialog):
    """Dialog for restoring files from backup."""

    restore_completed = Signal(int)  # number of files restored

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("文件恢复 — ClearSameFile 备份管理")
        self.setMinimumSize(850, 550)
        self._sessions: List[dict] = []
        self._file_checks: dict[str, dict] = {}  # backup_path → entry dict
        self._build_ui()
        self._load_sessions()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Info label
        info = QLabel(
            "以下是从本工具删除并备份的文件。选择要恢复的文件，点击「恢复选中」将其还原到原始位置。"
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #555; font-size: 12px;")
        layout.addWidget(info)

        # Splitter: sessions tree | file list
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Sessions panel
        self.session_tree = QTreeWidget()
        self.session_tree.setHeaderLabels(["备份会话", "文件数", "大小"])
        self.session_tree.setColumnWidth(0, 200)
        self.session_tree.setColumnWidth(1, 60)
        self.session_tree.setColumnWidth(2, 80)
        self.session_tree.setRootIsDecorated(True)
        self.session_tree.currentItemChanged.connect(self._on_session_selected)
        splitter.addWidget(self.session_tree)

        # Files panel
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self.file_table = QTableWidget()
        self.file_table.setColumnCount(5)
        self.file_table.setHorizontalHeaderLabels(["恢复", "文件名", "原始路径", "大小", "状态"])
        self.file_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.file_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.file_table.setAlternatingRowColors(True)
        self.file_table.verticalHeader().setVisible(False)

        hh = self.file_table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.file_table.setColumnWidth(0, 50)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.file_table.setColumnWidth(1, 160)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.file_table.setColumnWidth(3, 80)
        hh.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.file_table.setColumnWidth(4, 80)

        right_layout.addWidget(self.file_table)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        layout.addWidget(splitter)

        # Bottom buttons
        btn_row = QHBoxLayout()
        self.select_all_btn = QPushButton("全选可恢复文件")
        self.select_all_btn.clicked.connect(lambda: self._select_all(True))
        self.deselect_btn = QPushButton("取消全选")
        self.deselect_btn.clicked.connect(lambda: self._select_all(False))

        self.delete_session_btn = QPushButton("永久删除此会话")
        self.delete_session_btn.setStyleSheet("color: #d9534f;")
        self.delete_session_btn.clicked.connect(self._delete_session)

        self.restore_btn = QPushButton("恢复选中文件")
        self.restore_btn.setMinimumHeight(34)
        self.restore_btn.setMinimumWidth(120)
        self.restore_btn.setStyleSheet(
            "QPushButton { background-color: #5cb85c; color: white; font-weight: bold; border-radius: 4px; padding: 6px 16px; }"
            "QPushButton:hover { background-color: #4cae4c; }"
        )
        self.restore_btn.clicked.connect(self._restore_selected)

        btn_row.addWidget(self.select_all_btn)
        btn_row.addWidget(self.deselect_btn)
        btn_row.addStretch()
        btn_row.addWidget(self.delete_session_btn)
        btn_row.addWidget(self.restore_btn)
        layout.addLayout(btn_row)

    def _load_sessions(self):
        self._sessions = backup.get_backup_sessions()
        self.session_tree.clear()
        for s in self._sessions:
            item = QTreeWidgetItem([
                s["session_name"],
                str(s.get("total_files", 0)),
                format_size(s.get("total_size", 0)),
            ])
            item.setData(0, Qt.ItemDataRole.UserRole, s["session_dir"])
            self.session_tree.addTopLevelItem(item)

        if self.session_tree.topLevelItemCount() > 0:
            self.session_tree.setCurrentItem(self.session_tree.topLevelItem(0))

    def _on_session_selected(self, current, previous):
        self.file_table.setRowCount(0)
        self._file_checks.clear()

        if current is None:
            self._update_restore_button()
            return

        session_dir = current.data(0, Qt.ItemDataRole.UserRole)
        files = backup.get_session_files(session_dir)

        self.file_table.setRowCount(len(files))
        for row, entry in enumerate(files):
            exists = entry.get("exists", False)

            cb = QCheckBox()
            cb.setEnabled(exists)
            cb.stateChanged.connect(
                lambda state, e=entry, cb=cb: self._on_file_checked(e, cb)
            )
            cb_widget = QWidget()
            cl = QHBoxLayout(cb_widget)
            cl.addWidget(cb)
            cl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cl.setContentsMargins(0, 0, 0, 0)
            self.file_table.setCellWidget(row, 0, cb_widget)

            fname = os.path.basename(entry["original"])
            self.file_table.setItem(row, 1, QTableWidgetItem(fname))
            self.file_table.setItem(row, 2, QTableWidgetItem(entry["original"]))

            size_item = QTableWidgetItem(format_size(entry.get("size", 0)))
            size_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.file_table.setItem(row, 3, size_item)

            status = "可恢复" if exists else "已不存在"
            self.file_table.setItem(row, 4, QTableWidgetItem(status))
            self.file_table.setRowHeight(row, 26)

        self._update_restore_button()

    def _on_file_checked(self, entry, cb):
        if cb.isChecked():
            self._file_checks[entry["backup"]] = entry
        else:
            self._file_checks.pop(entry["backup"], None)
        self._update_restore_button()

    def _update_restore_button(self):
        count = len(self._file_checks)
        self.restore_btn.setText(f"恢复选中 ({count})" if count else "恢复选中文件")
        self.restore_btn.setEnabled(count > 0)

    def _select_all(self, select: bool):
        for row in range(self.file_table.rowCount()):
            cb_widget = self.file_table.cellWidget(row, 0)
            if cb_widget:
                cb = cb_widget.findChild(QCheckBox)
                if cb and cb.isEnabled():
                    cb.setChecked(select)

    def _restore_selected(self):
        if not self._file_checks:
            return

        entries = list(self._file_checks.values())
        result = backup.restore_files(entries)

        msg = (
            f"恢复完成:\n"
            f"  成功: {result['success']} 个\n"
            f"  失败: {result['failed']} 个\n"
            f"  跳过(目标已存在): {result['skipped']} 个"
        )
        QMessageBox.information(self, "恢复结果", msg)

        if result["success"] > 0:
            self.restore_completed.emit(result["success"])

        # Refresh
        self._load_sessions()
        self.file_table.setRowCount(0)
        self._file_checks.clear()
        self._update_restore_button()

    def _delete_session(self):
        current = self.session_tree.currentItem()
        if current is None:
            return
        session_dir = current.data(0, Qt.ItemDataRole.UserRole)
        session_name = current.text(0)

        reply = QMessageBox.question(
            self, "确认永久删除",
            f"确定要永久删除备份会话「{session_name}」中的所有文件吗？\n\n此操作不可撤销！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            backup.delete_backup_session(session_dir)
            self._load_sessions()
            self.file_table.setRowCount(0)
            self._file_checks.clear()
            self._update_restore_button()
