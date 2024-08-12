from __future__ import annotations

import os
import sys

import qdarktheme
from PySide6.QtCore import QSettings
from PySide6.QtCore import Qt
from PySide6.QtCore import QThread
from PySide6.QtCore import Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QApplication
from PySide6.QtWidgets import QComboBox
from PySide6.QtWidgets import QFormLayout
from PySide6.QtWidgets import QGroupBox
from PySide6.QtWidgets import QHBoxLayout
from PySide6.QtWidgets import QLabel
from PySide6.QtWidgets import QMainWindow
from PySide6.QtWidgets import QPushButton
from PySide6.QtWidgets import QSlider
from PySide6.QtWidgets import QSplitter
from PySide6.QtWidgets import QVBoxLayout
from PySide6.QtWidgets import QWidget

from src.Core import Core
from src.Widgets import AnalyserWidget
from src.Widgets import Graph
from src.Widgets import PixmapWidget


class CommandWorker(QThread):  # type: ignore
    finished = Signal()  # Signal to notify when the command execution is finished

    def __init__(self, command: str) -> None:
        super().__init__()
        self.command = command

    def run(self) -> None:
        os.system(self.command)  # Run the command
        self.finished.emit()  # Emit signal when done


# Define the main window
class MainWindow(QMainWindow):  # type: ignore
    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("Awesome Ballbar")

        self.core = Core()  # where all the magic happens

        # Widgets:
        self.left_splitter = QSplitter()
        self.middle_splitter = QSplitter()
        self.right_splitter = QSplitter(Qt.Orientation.Vertical)
        sensor_feed_box = QGroupBox("Sensor Feed")
        analyser_box = QGroupBox("Analyser")
        control_box = QGroupBox("Control")
        plot_box = QGroupBox("Plot")
        commands_box = QGroupBox("Commands")

        start_btn = QPushButton("Start")
        stop_btn = QPushButton("Stop")
        reset_btn = QPushButton("Reset")

        self.analyser_widget = AnalyserWidget()
        self.sensor_feed_widget = PixmapWidget()
        self.camera_combo = QComboBox()

        self.smoothing = QSlider(Qt.Horizontal)
        self.smoothing.setRange(0, 200)
        self.smoothing.setTickInterval(1)

        self.graph = Graph(self.core.samples)

        # Layouts
        control_layout = QHBoxLayout()
        commands_layout = QVBoxLayout()
        for btn in [start_btn, stop_btn, reset_btn]:
            btn.setFixedHeight(60)
            commands_layout.addWidget(btn)
        commands_layout.addStretch()
        commands_box.setLayout(commands_layout)
        control_layout.addWidget(commands_box)
        control_box.setLayout(control_layout)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        plot_layout = QVBoxLayout()
        plot_layout.addWidget(self.graph)

        # Attach Widgets
        camera_form = QFormLayout()
        camera_form.addRow(QLabel("Camera:"), self.camera_combo)
        sensor_layout = QVBoxLayout()
        sensor_layout.addLayout(camera_form)
        sensor_layout.addWidget(self.sensor_feed_widget)
        sensor_feed_box.setLayout(sensor_layout)

        analyser_form = QFormLayout()
        analyser_form.addRow("Smoothing", self.smoothing)
        analyser_layout = QVBoxLayout()
        analyser_layout.addLayout(analyser_form)
        analyser_layout.addWidget(self.analyser_widget)
        analyser_box.setLayout(analyser_layout)

        plot_box.setLayout(plot_layout)

        self.left_splitter.addWidget(sensor_feed_box)
        self.left_splitter.addWidget(analyser_box)
        self.right_splitter.addWidget(control_box)
        self.right_splitter.addWidget(plot_box)

        self.middle_splitter.addWidget(self.left_splitter)
        self.middle_splitter.addWidget(self.right_splitter)
        main_layout.addWidget(self.middle_splitter)

        # Logic
        for cam in self.core.get_cameras():
            self.camera_combo.addItem(cam)

        self.core.set_camera(self.camera_combo.currentIndex())

        # Signals
        self.core.frameWorker.OnAnalyserUpdate.connect(self.analyser_widget.set_data)
        self.sensor_feed_widget.OnHeightChanged.connect(self.analyser_widget.setMaximumHeight)
        self.sensor_feed_widget.OnHeightChanged.connect(
            lambda value: setattr(self.core.frameWorker, "analyser_widget_height", value)
        )
        self.core.frameWorker.OnPixmapChanged.connect(self.sensor_feed_widget.setPixmap)
        self.smoothing.valueChanged.connect(lambda value: setattr(self.core.frameWorker, "analyser_smoothing", value))
        start_btn.clicked.connect(self.run_ballbar)

        self.load_settings()

    def run_ballbar(self) -> None:
        print("starting ballbar check")
        command = "python src/linuxcnc_ballbar_check.py run"

        # Create and start the worker thread
        self.command_worker = CommandWorker(command)
        self.command_worker.finished.connect(self.on_command_finished)  # Connect signal to slot
        self.command_worker.start()

    def on_command_finished(self) -> None:
        print("Ballbar check completed.")

    def load_settings(self) -> None:
        settings = QSettings("awesome-ballbar", "AwesomeBallbar")
        if settings.contains("geometry"):
            self.restoreGeometry(settings.value("geometry"))

        if settings.contains("left_splitter"):
            self.left_splitter.setSizes([int(i) for i in settings.value("left_splitter")])
        if settings.contains("middle_splitter"):
            self.middle_splitter.setSizes([int(i) for i in settings.value("middle_splitter")])
        if settings.contains("right_splitter"):
            self.right_splitter.setSizes([int(i) for i in settings.value("right_splitter")])
        if settings.contains("smoothing"):
            self.smoothing.setValue(int(settings.value("smoothing")))

    def closeEvent(self, event: QCloseEvent) -> None:
        self.settings = QSettings("awesome-ballbar", "AwesomeBallbar")
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("left_splitter", self.left_splitter.sizes())
        self.settings.setValue("middle_splitter", self.middle_splitter.sizes())
        self.settings.setValue("right_splitter", self.right_splitter.sizes())
        self.settings.setValue("smoothing", self.smoothing.value())

        # Cleanup the threads
        self.core.workerThread.quit()
        self.core.workerThread.wait()
        self.core.sampleWorkerThread.quit()
        self.core.sampleWorkerThread.wait()

        # Close the ballbar thread

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
