"""Left sidebar: scan directory management, filters, controls, statistics."""

import os
from typing import List, Optional, Set

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QListWidget,
    QListWidgetItem, QPushButton, QProgressBar, QLabel, QFileDialog,
    QMessageBox, QTreeView, QAbstractItemView,
)
from PySide6.QtCore import Signal, Qt

from core.scanner import ScanConfig
from ui.dialogs import FilterDialog, format_size


class ScanPanel(QWidget):
    scan_requested = Signal(ScanConfig)
    stop_requested = Signal()
    trusted_dirs_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._filter_min = 0
        self._filter_max = 0
        self._filter_ext: Set[str] = set()
        self._filter_exclude: Set[str] = {"node_modules", ".git", "__pycache__"}
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # --- Directory group ---
        dir_group = QGroupBox("扫描目录")
        dir_layout = QVBoxLayout(dir_group)

        self.dir_list = QListWidget()
        self.dir_list.setAlternatingRowColors(True)
        self.dir_list.setMinimumHeight(120)
        dir_layout.addWidget(self.dir_list)

        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("+ 添加目录")
        self.add_btn.clicked.connect(self._add_directory)
        self.remove_btn = QPushButton("- 移除选中")
        self.remove_btn.clicked.connect(self._remove_directory)
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.remove_btn)
        dir_layout.addLayout(btn_layout)

        layout.addWidget(dir_group)

        # --- Trusted directory group ---
        trusted_group = QGroupBox("信任目录 (优先保留)")
        trusted_group.setToolTip("信任目录内的文件将被优先保留，其余文件自动标记为删除")
        trusted_layout = QVBoxLayout(trusted_group)

        self.trusted_list = QListWidget()
        self.trusted_list.setAlternatingRowColors(True)
        self.trusted_list.setMaximumHeight(80)
        trusted_layout.addWidget(self.trusted_list)

        t_btn_layout = QHBoxLayout()
        self.t_add_btn = QPushButton("+ 批量添加")
        self.t_add_btn.setToolTip("可连续选择多个目录，点取消完成添加")
        self.t_add_btn.clicked.connect(self._add_trusted_directory)
        self.t_remove_btn = QPushButton("- 移除")
        self.t_remove_btn.clicked.connect(self._remove_trusted_directory)
        t_btn_layout.addWidget(self.t_add_btn)
        t_btn_layout.addWidget(self.t_remove_btn)
        t_btn_layout.addStretch()
        trusted_layout.addLayout(t_btn_layout)

        layout.addWidget(trusted_group)

        # --- Filter button ---
        self.filter_btn = QPushButton("过滤设置...")
        self.filter_btn.clicked.connect(self._open_filter_dialog)
        self.filter_label = QLabel("过滤: 无限制")
        self.filter_label.setWordWrap(True)
        self.filter_label.setStyleSheet("color: gray; font-size: 11px;")

        filter_h = QHBoxLayout()
        filter_h.addWidget(self.filter_btn)
        filter_h.addWidget(self.filter_label, 1)
        layout.addLayout(filter_h)

        # --- Scan controls ---
        ctrl_layout = QHBoxLayout()
        self.scan_btn = QPushButton("开始扫描")
        self.scan_btn.setMinimumHeight(36)
        self.scan_btn.clicked.connect(self._start_scan)
        self.stop_btn = QPushButton("停止")
        self.stop_btn.setMinimumHeight(36)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop_scan)
        ctrl_layout.addWidget(self.scan_btn)
        ctrl_layout.addWidget(self.stop_btn)
        layout.addLayout(ctrl_layout)

        # --- Progress ---
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_label = QLabel("")
        self.progress_label.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.progress_label)

        # --- Statistics ---
        stats_group = QGroupBox("统计信息")
        stats_layout = QVBoxLayout(stats_group)
        self.stat_files = QLabel("扫描文件: 0")
        self.stat_duplicates = QLabel("重复文件: 0")
        self.stat_wasted = QLabel("可释放: 0 B")
        stats_layout.addWidget(self.stat_files)
        stats_layout.addWidget(self.stat_duplicates)
        stats_layout.addWidget(self.stat_wasted)
        layout.addWidget(stats_group)

        layout.addStretch()

    def _add_directory(self):
        d = QFileDialog.getExistingDirectory(self, "选择扫描目录")
        if d:
            # avoid duplicates
            for i in range(self.dir_list.count()):
                if self.dir_list.item(i).text() == d:
                    return
            self.dir_list.addItem(d)

    def _remove_directory(self):
        for item in self.dir_list.selectedItems():
            self.dir_list.takeItem(self.dir_list.row(item))

    def _add_trusted_directory(self):
        dlg = QFileDialog(self, "选择信任目录（可多选）")
        dlg.setFileMode(QFileDialog.FileMode.Directory)
        dlg.setOption(QFileDialog.Option.DontUseNativeDialog, True)
        dlg.setOption(QFileDialog.Option.ShowDirsOnly, True)

        # Enable multi-selection on the internal tree view
        for child in dlg.findChildren(QTreeView):
            child.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
            break

        if dlg.exec() != QFileDialog.DialogCode.Accepted:
            return

        dirs = dlg.selectedFiles()
        added = False
        for d in dirs:
            for i in range(self.trusted_list.count()):
                if self.trusted_list.item(i).text() == d:
                    break
            else:
                self.trusted_list.addItem(d)
                added = True
        if added:
            self.trusted_dirs_changed.emit()

    def _remove_trusted_directory(self):
        if not self.trusted_list.selectedItems():
            return
        for item in self.trusted_list.selectedItems():
            self.trusted_list.takeItem(self.trusted_list.row(item))
        self.trusted_dirs_changed.emit()

    def get_trusted_directories(self) -> List[str]:
        return [self.trusted_list.item(i).text() for i in range(self.trusted_list.count())]

    def set_trusted_directories(self, dirs: List[str]) -> None:
        self.trusted_list.clear()
        for d in dirs:
            if d:
                self.trusted_list.addItem(d)

    def _open_filter_dialog(self):
        dlg = FilterDialog(
            self,
            current_min=self._filter_min,
            current_max=self._filter_max,
            current_ext=",".join(sorted(self._filter_ext)),
            current_exclude=",".join(sorted(self._filter_exclude)),
        )
        if dlg.exec():
            vals = dlg.get_values()
            self._filter_min = vals["min_size"]
            self._filter_max = vals["max_size"]
            self._filter_ext = {e.strip().lower() for e in vals["extensions"].split(",") if e.strip()}
            self._filter_exclude = {e.strip() for e in vals["exclude_dirs"].split(",") if e.strip()}
            self._update_filter_label()

    def _update_filter_label(self):
        parts = []
        if self._filter_min > 0:
            parts.append(f"最小 {format_size(self._filter_min)}")
        if self._filter_max > 0:
            parts.append(f"最大 {format_size(self._filter_max)}")
        if self._filter_ext:
            parts.append(f"类型: {', '.join(self._filter_ext)}")
        if self._filter_exclude:
            parts.append(f"排除: {', '.join(self._filter_exclude)}")
        self.filter_label.setText("过滤: " + (", ".join(parts) if parts else "无限制"))

    def _start_scan(self):
        dirs = [self.dir_list.item(i).text() for i in range(self.dir_list.count())]
        if not dirs:
            QMessageBox.warning(self, "提示", "请先添加扫描目录。")
            return

        config = ScanConfig(
            directories=dirs,
            min_size=self._filter_min,
            max_size=self._filter_max,
            extensions=self._filter_ext,
            exclude_dirs=self._filter_exclude,
        )

        self.scan_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # indeterminate
        self.progress_label.setText("准备扫描...")

        self.scan_requested.emit(config)

    def _stop_scan(self):
        self.stop_requested.emit()
        self.stop_btn.setEnabled(False)
        self.progress_label.setText("正在停止...")

    # --- callbacks from main window ---

    def on_scan_progress(self, stage: str, current: int, total: int):
        self.progress_label.setText(f"{stage} ({current}/{total})" if total else stage)
        if total > 0:
            self.progress_bar.setRange(0, total)
            self.progress_bar.setValue(current)

    def on_scan_finished(self, total_files: int, duplicate_files: int, wasted_size: int):
        self.scan_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.progress_label.setText("扫描完成")

        self.stat_files.setText(f"扫描文件: {total_files:,}")
        self.stat_duplicates.setText(f"重复文件: {duplicate_files:,}")
        self.stat_wasted.setText(f"可释放: {format_size(wasted_size)}")

    def on_scan_error(self, msg: str):
        self.scan_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.progress_label.setText(f"扫描出错: {msg}")
        QMessageBox.critical(self, "扫描错误", msg)
