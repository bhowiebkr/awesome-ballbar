from __future__ import annotations

import os
import pickle
import sys
from typing import List

import qdarktheme
from PySide6.QtCore import QSettings
from PySide6.QtCore import Qt
from PySide6.QtCore import QThread
from PySide6.QtCore import Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QApplication
from PySide6.QtWidgets import QComboBox
from PySide6.QtWidgets import QFileDialog
from PySide6.QtWidgets import QFormLayout
from PySide6.QtWidgets import QGroupBox
from PySide6.QtWidgets import QHBoxLayout
from PySide6.QtWidgets import QLabel
from PySide6.QtWidgets import QMainWindow
from PySide6.QtWidgets import QMessageBox
from PySide6.QtWidgets import QPushButton
from PySide6.QtWidgets import QSlider
from PySide6.QtWidgets import QSplitter
from PySide6.QtWidgets import QVBoxLayout
from PySide6.QtWidgets import QWidget

from src.Core import Core
from src.data_filtering import filter_and_isolate_data
from src.DataClasses import FastData
from src.Widgets import AnalyserWidget
from src.Widgets import FloatLineEdit
from src.Widgets import Graph
from src.Widgets import PixmapWidget


class CommandWorker(QThread):  # type: ignore
    finished = Signal()  # Signal to notify when the command execution is finished

    def __init__(self, command: str) -> None:
        super().__init__()
        self.command = command

    def run(self) -> None:
        os.system(self.command)  # Run the command
        # no need to emit finished as it will by default from the QThread


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
        settings_box = QGroupBox("Settings")
        self.sensor_width = FloatLineEdit()

        start_btn = QPushButton("Start")

        self.data: List[float] = []

        self.analyser_widget = AnalyserWidget()
        self.sensor_feed_widget = PixmapWidget()
        self.camera_combo = QComboBox()

        self.smoothing = QSlider(Qt.Horizontal)
        self.smoothing.setRange(0, 200)
        self.smoothing.setTickInterval(1)
        save_btn = QPushButton("Save")
        load_btn = QPushButton("Load")

        self.graph = Graph()

        # Layouts
        settings_form = QFormLayout()
        settings_form.addRow("Sensor Width", self.sensor_width)

        settings_layout = QVBoxLayout()
        settings_layout.addLayout(settings_form)
        settings_layout.addWidget(save_btn)
        settings_layout.addWidget(load_btn)
        settings_box.setLayout(settings_layout)

        control_layout = QHBoxLayout()
        commands_layout = QVBoxLayout()
        for btn in [start_btn]:
            btn.setFixedHeight(60)
            commands_layout.addWidget(btn)
        commands_layout.addStretch()
        commands_box.setLayout(commands_layout)
        control_layout.addWidget(settings_box)
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
        start_btn.clicked.connect(self.prep_ballbar)
        self.sensor_width.textChanged.connect(self.core.frameWorker.set_sensor_width_mm)
        self.sensor_width.setText("5.5")

        load_btn.clicked.connect(self.load_data_gui)

        self.load_settings()

        # DEBUGGING
        self.load_pickle("/home/howard/Documents/awesome-ballbar/ballbar_04.pkl")

    def load_data_gui(self):
        """Open a file dialog to select a pickle file and load its content into self.data."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Pickle File", "", "Pickle Files (*.pkl);;All Files (*)")
        if file_path:
            print(f"loading file: {file_path}")
            self.load_pickle(file_path)

    def load_pickle(self, file_path):
        """Load data from a pickle file into self.data."""
        with open(file_path, "rb") as file:
            self.data = pickle.load(file)

        self.update_graph()

    def prep_ballbar(self) -> None:
        command = "python src/linuxcnc_ballbar_check.py prep"

        # Create and start the worker thread for preparation
        self.prep_worker = CommandWorker(command)
        self.prep_worker.finished.connect(self.show_ballbar_message)  # Connect signal to show message
        self.prep_worker.start()

    def show_ballbar_message(self) -> None:
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setWindowTitle("Install Ballbar")
        msg_box.setText("Please install the ballbar and then click Continue.")
        msg_box.setStandardButtons(QMessageBox.Ok)
        continue_button = msg_box.button(QMessageBox.Ok)
        continue_button.setText("Continue")

        # Show the message box and connect its button click to run_ballbar
        if msg_box.exec() == QMessageBox.Ok:
            self.run_ballbar()

    def store_data(self, data: FastData) -> None:
        self.data.append(data.sample_micron_value)

    def run_ballbar(self) -> None:
        # Connect up the data feed and store the result
        self.data = []
        self.core.frameWorker.OnAnalyserUpdate.connect(self.store_data)

        command = "python src/linuxcnc_ballbar_check.py run"

        # Create and start the worker thread for running the ballbar check
        self.run_worker = CommandWorker(command)
        self.run_worker.finished.connect(self.run_finished)  # Connect signal to indicate completion
        self.run_worker.start()

    def run_finished(self) -> None:
        self.core.frameWorker.OnAnalyserUpdate.disconnect(self.store_data)
        print("Ballbar check finished.")

        print(f"total samples: {len(self.data)} samples per degree = {len(self.data)/360}")

        self.update_graph()

        # Base filename
        base_filename = "ballbar_"
        extension = ".pkl"
        i = 1

        # Determine the correct filename
        while True:
            filename = f"{base_filename}{i:02d}{extension}"
            if not os.path.exists(filename):
                break
            i += 1

        # Write the array to a pickle file
        with open(filename, "wb") as file:
            pickle.dump(self.data, file)

    def update_graph(self):
        threshold = 700
        isolated_data = filter_and_isolate_data(self.data, threshold)

        clockwise = isolated_data["clockwise"][0]
        clockwise.reverse()
        counterclockwise = isolated_data["counterclockwise"][0]

        print("Clockwise Data:", len(clockwise))
        print("Counterclockwise Data:", len(counterclockwise))

        self.graph.set_data(clockwise, counterclockwise)

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
