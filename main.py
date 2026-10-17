"""
PC Performance Monitor - Application Entry Point
Launches the PySide6 desktop monitor application.
"""

from __future__ import annotations

import signal
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from ui import MainWindow


def main() -> int:
    # Allow clean exit with Ctrl+C in terminal
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    app = QApplication(sys.argv)
    app.setApplicationName("PC Performance Monitor")
    app.setOrganizationName("SystemTools")

    # Set a clean default font
    font = QFont("Segoe UI", 9)
    app.setFont(font)

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
