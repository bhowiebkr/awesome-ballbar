from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtGui import QPixmap


@dataclass
class FastData:
    def __init__(self, pixmap: QPixmap, sample_pixel_space_value: float, sample_micron_value: float) -> None:
        self.pixmap = pixmap
        self.sample_pixel_space_value = sample_pixel_space_value
        self.sample_micron_value = sample_micron_value
