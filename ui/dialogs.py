"""Dialog windows for the application."""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QDialogButtonBox, QFormLayout, QLineEdit, QSpinBox,
)
from PySide6.QtCore import Qt


class ConfirmDeleteDialog(QDialog):
    def __init__(self, file_count: int, total_size: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("确认删除")
        self.setMinimumWidth(400)
        self._result = False

        layout = QVBoxLayout(self)

        warning = QLabel(
            f"<b>确定要删除以下文件吗？</b><br><br>"
            f"文件数量: {file_count}<br>"
            f"总大小: {format_size(total_size)}<br><br>"
            f"文件将被移动到<b>回收站</b>，可随时恢复。"
        )
        warning.setWordWrap(True)
        layout.addWidget(warning)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Yes | QDialogButtonBox.StandardButton.No
        )
        buttons.setCenterButtons(True)
        buttons.button(QDialogButtonBox.StandardButton.Yes).setText("确认删除")
        buttons.button(QDialogButtonBox.StandardButton.No).setText("取消")
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_accept(self):
        self._result = True
        self.accept()

    @property
    def confirmed(self) -> bool:
        return self._result


class FilterDialog(QDialog):
    """Dialog for scan filter settings."""

    def __init__(self, parent=None, current_min=0, current_max=0,
                 current_ext="", current_exclude="node_modules,.git,__pycache__"):
        super().__init__(parent)
        self.setWindowTitle("扫描过滤设置")
        self.setMinimumWidth(450)

        layout = QFormLayout(self)

        self.min_size = QSpinBox()
        self.min_size.setRange(0, 999999)
        self.min_size.setSuffix(" MB")
        self.min_size.setValue(current_min // (1024 * 1024) if current_min else 0)
        self.min_size.setToolTip("0 = 不限制")
        layout.addRow("最小文件大小:", self.min_size)

        self.max_size = QSpinBox()
        self.max_size.setRange(0, 999999)
        self.max_size.setSuffix(" MB")
        self.max_size.setValue(current_max // (1024 * 1024) if current_max else 0)
        self.max_size.setToolTip("0 = 不限制")
        layout.addRow("最大文件大小:", self.max_size)

        self.extensions = QLineEdit()
        self.extensions.setPlaceholderText(".jpg,.png,.mp4  留空 = 所有文件")
        self.extensions.setText(current_ext)
        layout.addRow("文件类型:", self.extensions)

        self.exclude_dirs = QLineEdit()
        self.exclude_dirs.setText(current_exclude)
        layout.addRow("排除目录:", self.exclude_dirs)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_values(self) -> dict:
        return {
            "min_size": self.min_size.value() * 1024 * 1024,
            "max_size": self.max_size.value() * 1024 * 1024,
            "extensions": self.extensions.text().strip(),
            "exclude_dirs": self.exclude_dirs.text().strip(),
        }


def format_size(size_bytes: int) -> str:
    """Format bytes to human readable string."""
    if size_bytes >= 1024 * 1024 * 1024:
        return f"{size_bytes / (1024**3):.2f} GB"
    elif size_bytes >= 1024 * 1024:
        return f"{size_bytes / (1024**2):.2f} MB"
    elif size_bytes >= 1024:
        return f"{size_bytes / 1024:.2f} KB"
    else:
        return f"{size_bytes} B"
