from __future__ import annotations

import sys

import qdarktheme
from PySide6.QtCore import QSettings
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QApplication
from PySide6.QtWidgets import QMainWindow


# Define the main window
class MainWindow(QMainWindow):  # type: ignore
    def __init__(self) -> None:
        super().__init__()

        settings = QSettings("awesome-ballbar", "AwesomeBallbar")
        if settings.contains("geometry"):
            self.restoreGeometry(settings.value("geometry"))

    def closeEvent(self, event: QCloseEvent) -> None:
        self.settings = QSettings("awesome-ballbar", "AwesomeBallbar")
        self.settings.setValue("geometry", self.saveGeometry())
        self.deleteLater()
        super().closeEvent(event)


def start() -> None:
    app = QApplication(sys.argv)
    qdarktheme.setup_theme(additional_qss="QToolTip {color: black;}")

    window = MainWindow()

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    start()
