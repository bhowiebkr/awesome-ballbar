from __future__ import annotations

from typing import Any

import numpy as np
import qimage2ndarray
from PySide6.QtCore import QObject
from PySide6.QtCore import Signal
from PySide6.QtCore import Slot
from PySide6.QtGui import QImage
from PySide6.QtGui import QPixmap
from PySide6.QtGui import QTransform
from PySide6.QtMultimedia import QVideoFrame

from src.curves import fit_gaussian
from src.DataClasses import FastData


class FrameWorker(QObject):  # type: ignore
    OnPixmapChanged = Signal(QPixmap)
    OnAnalyserUpdate = Signal(FastData)

    def __init__(self, parent_obj: Any):
        super().__init__(None)
        self.ready = True
        self.analyser_smoothing = 0
        self.centre = 0.0
        self.analyser_widget_height = 0
        self.parent_obj = parent_obj
        self.data_width = 0

        self.sensor_width_mm = 10000000.0

    def set_sensor_width_mm(self, sensor_width_mm: float) -> None:
        if not sensor_width_mm:
            self.sensor_width_mm = 0.0
        else:
            self.sensor_width_mm = float(sensor_width_mm)

    @Slot(QVideoFrame)  # type: ignore
    def setVideoFrame(self, frame: QVideoFrame) -> None:
        self.ready = False

        # Get the frame as a gray scale image
        image = frame.toImage().convertToFormat(QImage.Format_Grayscale8)
        try:
            histo = np.mean(qimage2ndarray.raw_view(image), axis=0)
        except ValueError as e:
            print("Invalid QImage:", e)
            return

        pixmap = QPixmap.fromImage(image).transformed(QTransform().rotate(-90))

        self.OnPixmapChanged.emit(pixmap)

        # Create the smoothing kernel
        kernel = np.ones(2 * self.analyser_smoothing + 1) / (2 * self.analyser_smoothing + 1)

        # Apply convolution with 'valid' mode
        smoothed_histo = np.convolve(histo, kernel, mode="valid")

        # Generate x values for interpolation
        x = np.linspace(0, len(smoothed_histo) - 1, len(smoothed_histo))
        x_new = np.linspace(0, len(smoothed_histo) - 1, pixmap.height())

        # Interpolate to match original length
        resized_histo = np.interp(x_new, x, smoothed_histo)

        # Find the min and max values
        min_value, max_value = resized_histo.min(), resized_histo.max()

        # Rescale the intensity values to have a range between 0 and 255
        normal_histo = ((resized_histo - min_value) * (255.0 / (max_value - min_value))).clip(0, 255).astype(np.uint8)

        # Generate the image
        # Define the scope image data as the width (long side) of the image x 256 for pixels
        scopeData = np.zeros((normal_histo.shape[0], 256), dtype=np.uint8)

        # Replace NaN values with 0
        self.histo = np.nan_to_num(normal_histo)

        sample_pixel_position = fit_gaussian(self.histo)  # Specify the y position of the line

        sensor_height_pixels = pixmap.height()
        middle_pixel_position = sensor_height_pixels / 2
        pixel_to_micron = self.sensor_width_mm / sensor_height_pixels * 1000
        sample_micron_value = sample_pixel_position * pixel_to_micron
        middle_micron_offset = middle_pixel_position * pixel_to_micron
        sample_micron_value -= middle_micron_offset

        # Set scope data
        for i, intensity in enumerate(self.histo):
            scopeData[i, : int(intensity)] = 128

        # Create QImage directly from the scope data
        qimage = QImage(
            scopeData.data,
            scopeData.shape[1],
            scopeData.shape[0],
            scopeData.strides[0],
            QImage.Format_Grayscale8,
        )

        # Create QPixmap from QImage
        scope_image = QPixmap.fromImage(qimage)

        # Create a vertical flip transform and apply it to the QPixmap
        scope_image = scope_image.transformed(QTransform().scale(1, -1))

        frame_data = FastData(scope_image, sample_pixel_position, sample_micron_value)
        self.OnAnalyserUpdate.emit(frame_data)

        self.ready = True


class FrameSender(QObject):  # type: ignore
    OnFrameChanged = Signal(QVideoFrame)
