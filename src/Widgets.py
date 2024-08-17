from __future__ import annotations

from typing import Any
from typing import List
from typing import Optional

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PySide6.QtCore import QRegularExpression
from PySide6.QtCore import Qt
from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from PySide6.QtGui import QFont
from PySide6.QtGui import QKeyEvent
from PySide6.QtGui import QPainter
from PySide6.QtGui import QPaintEvent
from PySide6.QtGui import QPen
from PySide6.QtGui import QPixmap
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import QLineEdit
from PySide6.QtWidgets import QSizePolicy
from PySide6.QtWidgets import QTableWidgetItem
from PySide6.QtWidgets import QVBoxLayout
from PySide6.QtWidgets import QWidget

from src.DataClasses import FastData
from src.utils import get_units

# from src.DataClasses import Sample

style = {
    "axes.grid": "True",
    "axes.edgecolor": "white",
    "axes.linewidth": "0",
    "xtick.major.size": "0",
    "ytick.major.size": "0",
    "xtick.minor.size": "0",
    "ytick.minor.size": "0",
    "text.color": "0.9",
    "axes.labelcolor": "0.9",
    "xtick.color": "0.9",
    "ytick.color": "0.9",
    "grid.color": "2A3459",
    "font.sans-serif": "Overpass, Helvetica, Helvetica Neue, Arial, Liberation \
        Sans, DejaVu Sans, Bitstream Vera Sans, sans-serif",
    "figure.facecolor": "202124",
    "axes.facecolor": "101012",
    "savefig.facecolor": "212946",
    "image.cmap": "RdPu",
}
plt.style.use(style)


class Graph(QWidget):
    def __init__(self, padding: float = 0.05):
        super().__init__()

        self.samples1: List[float] = []
        self.samples2: List[float] = []
        self.units = ""
        self.padding = padding  # Padding variable

        # Layouts
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Polar chart
        fig, self.ax = plt.subplots(subplot_kw={"projection": "polar"})
        fig.tight_layout(pad=self.padding)
        fig.subplots_adjust(left=self.padding, right=1 - self.padding, top=1 - self.padding, bottom=self.padding)
        self.canvas = FigureCanvas(fig)

        self.ax.set_ylabel(self.units)
        self.ax.margins(0)
        self.ax.set_position([self.padding, self.padding, 1 - 2 * self.padding, 1 - 2 * self.padding])
        self.ax.autoscale_view("tight")

        main_layout.addWidget(self.canvas)

    def update_graph(self) -> None:
        # Clear the axis and plot the data
        self.ax.clear()

        if not self.samples1 and not self.samples2:
            self.canvas.draw()
            return

        num_samples1 = len(self.samples1)
        num_samples2 = len(self.samples2)
        theta1 = np.linspace(0, 2 * np.pi, num_samples1, endpoint=False)
        theta2 = np.linspace(0, 2 * np.pi, num_samples2, endpoint=False)
        r1 = np.array(self.samples1)
        r2 = np.array(self.samples2)

        # Ensure the graph wraps around by appending the first point to the end
        theta1 = np.concatenate([theta1, [theta1[0]]])
        r1 = np.concatenate([r1, [r1[0]]])
        theta2 = np.concatenate([theta2, [theta2[0]]])
        r2 = np.concatenate([r2, [r2[0]]])

        # Plot data points for both datasets
        self.ax.plot(theta1, r1, marker="", markersize=5, label="Counterclockwise", color="blue")
        self.ax.plot(theta2, r2, marker="", markersize=5, label="Clockwise", color="red")

        # Adjust radial limits based on data
        r_min = min(np.min(r1), np.min(r2))
        r_max = max(np.max(r1), np.max(r2))
        r_range = r_max - r_min
        padding = 0.1 * r_range  # Add some padding around the data

        self.ax.set_ylim(r_min - padding, r_max + padding)

        self.ax.legend()
        self.canvas.draw()

    def set_data(self, new_samples1: List[float], new_samples2: List[float]) -> None:
        """
        Update the graph with two sets of sample data.

        Args:
            new_samples1 (list): A list of float values representing the first set of sample data.
            new_samples2 (list): A list of float values representing the second set of sample data.
        """
        self.samples1 = new_samples1
        self.samples2 = new_samples2
        self.update_graph()


class PixmapWidget(QWidget):  # type: ignore
    OnHeightChanged = Signal(int)

    def __init__(self) -> None:
        super().__init__()

        self.pixmap = QPixmap(100, 100)
        self.pixmap.fill(QColor(0, 0, 0))

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)

        if not self.pixmap:
            return

        painter = QPainter(self)
        painter.drawPixmap(self.rect(), self.pixmap)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        new_height = event.size().height()
        self.OnHeightChanged.emit(new_height)

    def setPixmap(self, pixmap: QPixmap) -> None:
        self.pixmap = pixmap
        self.update()


class AnalyserWidget(QWidget):  # type: ignore
    def __init__(self, sensor_height_mm: float = 5.5) -> None:
        super().__init__()
        self.pixmap = QPixmap(100, 100)
        self.pixmap.fill(QColor(0, 0, 0))
        self.sample = 0  # location of the sample in pixel space on the widget
        self.zero = 960  # Center of the widget for zero (half of the sensor width)
        self.text = ""  # Text to display shows the distance from zero
        self.sensor_height_mm = sensor_height_mm  # Height of the sensor in mm
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)
        painter = QPainter(self)

        # Pixmap
        painter.drawPixmap(self.rect(), self.pixmap)

        # Determine the zero position to be the center of the widget
        self.zero = self.height() // 2

        # Zero line
        painter.setPen(Qt.red)
        painter.drawLine(0, self.zero, self.width(), self.zero)

        # Sample line relative to zero
        if self.sample is not None:
            sample_y = self.zero + self.sample
            pen = QPen(Qt.green, 0, Qt.SolidLine)
            painter.setPen(pen)
            painter.drawLine(0, sample_y, self.width(), sample_y)

        # Display the text showing the distance from zero in microns
        if self.text:
            painter.setFont(QFont("Arial", 12))
            painter.setPen(Qt.green)
            text_width = painter.fontMetrics().horizontalAdvance(self.text)
            text_height = painter.fontMetrics().height()
            x = (self.width() - text_width) / 2
            y = sample_y - (text_height / 2)
            painter.drawText(int(x), int(y), self.text)

    def set_data(self, data: FastData) -> None:
        self.pixmap = data.pixmap

        # Calculate the sample position relative to zero, using the input range (0.0-1920.0)
        self.sample = self.zero - (data.sample_pixel_space_value * self.height() / 1920.0)

        # Update the text to show the distance from zero in microns
        self.text = f"{data.sample_micron_value:+.2f} µm"
        self.update()


class TableUnit(QTableWidgetItem):  # type: ignore
    def __init__(self) -> None:
        super().__init__()
        self.units = ""
        self.value = 0.0

    def set_units(self, units: str) -> None:
        self.units = units

    def data(self, role: int) -> Any:
        super().data(role)
        if role == Qt.DisplayRole:
            return get_units(self.units, self.value)
        return None


class FloatLineEdit(QLineEdit):  # type: ignore
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        # Set up a regular expression for floating point numbers
        float_regex = QRegularExpression(r"^-?\d*\.?\d*$")  # Regex to match float numbers
        self.validator = QRegularExpressionValidator(float_regex, self)
        self.setValidator(self.validator)

        # Connect textChanged signal to validate input
        self.textChanged.connect(self.validate_text)

    def validate_text(self) -> None:
        """Validate the current text to ensure it's a valid float"""
        text = self.text()
        if text:
            try:
                # Try to convert the text to float
                float(text)
                self.setStyleSheet("")  # Clear any error styling
            except ValueError:
                # Invalid float; apply error styling
                self.setStyleSheet("border: 1px solid red;")
        else:
            self.setStyleSheet("")  # Clear any error styling if the text is empty

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Override to handle key events"""
        super().keyPressEvent(event)
        # Validate the text after the key press event
        self.validate_text()
