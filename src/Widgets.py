from __future__ import annotations

from typing import Any

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PySide6.QtCore import Qt
from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from PySide6.QtGui import QFont
from PySide6.QtGui import QPainter
from PySide6.QtGui import QPaintEvent
from PySide6.QtGui import QPen
from PySide6.QtGui import QPixmap
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import QSizePolicy
from PySide6.QtWidgets import QTableWidgetItem
from PySide6.QtWidgets import QVBoxLayout
from PySide6.QtWidgets import QWidget
from scipy.interpolate import CubicSpline

from src.DataClasses import FrameData
from src.DataClasses import Sample
from src.utils import get_units
from src.utils import units_of_measurements


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


class Graph(QWidget):  # type: ignore
    def __init__(self, samples: list[Sample], padding: float = 0.05):
        super().__init__()

        self.samples = samples
        self.units = ""
        self.selected_index = 0
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

    def set_selected_index(self, index: int) -> None:
        self.selected_index = index + 1
        self.update_graph()

    def set_units(self, units: str) -> None:
        self.units = units
        self.update_graph()

    def update_graph(self) -> None:
        # Clear the axis and plot the data
        self.ax.clear()

        if self.units is None or len(self.samples) == 0:
            self.canvas.draw()
            return

        unit_multiplier = units_of_measurements[self.units]

        theta = np.linspace(0, 2 * np.pi, len(self.samples))
        r = []

        # Raw points
        for s in self.samples:
            r.append(s.y * unit_multiplier)
        self.ax.plot(theta, r, marker="o", markersize=5, label="Samples")

        # Fit a smooth curve to the data points
        if len(theta) > 2:
            f = CubicSpline(theta, r, bc_type="clamped")
            smooth_theta = np.linspace(theta[0], theta[-1], 500)
            smooth_r = f(smooth_theta)
            self.ax.plot(smooth_theta, smooth_r, linewidth=2, label="Smooth")

        # Plot selected index
        if type(self.selected_index) is int and self.selected_index >= 0:
            selected_theta = theta[self.selected_index - 1]
            self.ax.plot([selected_theta, selected_theta], [0, max(r)], linewidth=7, color="#380000", zorder=-1)
            self.ax.set_alpha(0.2)

        self.ax.legend()
        self.canvas.draw()


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
        self.zero = 0  # center of the widget for zero
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
            textWidth = painter.fontMetrics().horizontalAdvance(self.text)
            textHeight = painter.fontMetrics().height()
            x = (self.width() - textWidth) / 2
            y = sample_y - (textHeight / 2)
            painter.drawText(int(x), int(y), self.text)

    def set_data(self, data: FrameData) -> None:
        self.pixmap = data.pixmap
        self.sample = data.sample - self.zero  # Adjust sample relative to zero

        # Calculate the sample position in microns
        pixel_to_mm = self.sensor_height_mm / self.height()  # Convert pixel height to mm
        sample_in_mm = self.sample * pixel_to_mm * -1  # Convert sample position to mm
        sample_in_microns = sample_in_mm * 1000  # Convert mm to microns

        # Update the text to show the distance from zero in microns
        self.text = f"{sample_in_microns:+.2f} µm"
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
