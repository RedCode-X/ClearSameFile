"""ClearSameFile — 重复文件清理工具 入口"""

import os
import sys
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName("ClearSameFile")
    app.setApplicationVersion("1.0")

    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "resources", "app.ico")
    if os.path.isfile(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
