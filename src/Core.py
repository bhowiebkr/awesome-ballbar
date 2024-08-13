from __future__ import annotations

import numpy as np
from PySide6.QtCore import QObject
from PySide6.QtCore import QThread
from PySide6.QtCore import Signal
from PySide6.QtCore import Slot
from PySide6.QtGui import QPixmap
from PySide6.QtMultimedia import QCamera
from PySide6.QtMultimedia import QMediaCaptureSession
from PySide6.QtMultimedia import QMediaDevices
from PySide6.QtMultimedia import QVideoFrame
from PySide6.QtMultimedia import QVideoSink

from src.Workers import FrameSender
from src.Workers import FrameWorker

# from src.DataClasses import Sample


class Core(QObject):  # type: ignore
    OnSensorFeedUpdate = Signal(QPixmap)
    OnAnalyserUpdate = Signal(list)
    OnSubsampleProgressUpdate = Signal(list)
    OnSampleComplete = Signal()
    OnUnitsChanged = Signal(str)

    def __init__(self) -> None:
        super().__init__()

        self.pixmap = None  # pixmap used for the camera feed
        self.histo = None  # histogram values used in analyser
        self.camera = QCamera()  # camera being used
        self.centre = 0.0  # The found centre of the histogram
        self.zero = 0.0  # The zero point
        self.analyser_widget_height = 0  # The height of the widget so we can calculate the offset
        self.subsamples = 0  # total number of subsamples
        self.outliers = 0  # percentage value of how many outliers to remove from a sample
        self.units = ""  # string representing the units
        self.sensor_width = 0  # width of the sensor in millimeters (mm)
        self.setting_zero_sample = False  # boolean if we are setting zero or a sample
        self.replacing_sample = False  # If we are replacing a sample
        self.replacing_sample_index = 0  # the index of the sample we are replacing
        self.line_data = np.empty(0)  # numpy array of the fitted line through the samples
        # self.samples: list[Sample] = []

        # Frame worker
        self.workerThread = QThread()
        self.captureSession = QMediaCaptureSession()
        self.frameSender = FrameSender()
        self.frameWorker = FrameWorker(parent_obj=self)
        self.frameWorker.moveToThread(self.workerThread)
        self.workerThread.start()

        self.captureSession.setVideoSink(QVideoSink(self))
        self.captureSession.videoSink().videoFrameChanged.connect(self.onFramePassedFromCamera)
        self.frameSender.OnFrameChanged.connect(self.frameWorker.setVideoFrame)

    # def subsample_progress_update(self, subsample: Sample) -> None:
    #     self.OnSubsampleProgressUpdate.emit([subsample, self.subsamples])  # current sample and total

    def set_units(self, units: str) -> None:
        self.units = units

        self.OnUnitsChanged.emit(self.units)

    def start_sample(self, zero: bool, replacing_sample: bool, replacing_sample_index: int) -> None:
        self.replacing_sample = replacing_sample
        self.replacing_sample_index = replacing_sample_index

        if zero:  # if we are zero, we reset everything
            self.line_data = np.empty(0)
            self.zero = 0.0

        self.setting_zero_sample = zero
        self.sample_worker.start(self.subsamples, self.outliers)

    @Slot(QVideoFrame)  # type: ignore
    def onFramePassedFromCamera(self, frame: QVideoFrame):
        if self.frameWorker.ready:
            self.frameSender.OnFrameChanged.emit(frame)

    def get_cameras(self) -> list[str]:
        cams = []
        for cam in QMediaDevices.videoInputs():
            cams.append(cam.description())

        return cams

    def set_camera(self, index: int) -> None:
        if self.camera:
            self.camera.stop()

        available_cameras = QMediaDevices.videoInputs()
        if not available_cameras:
            return

        camera_info = available_cameras[index]
        self.camera = QCamera(cameraDevice=camera_info, parent=self)

        self.captureSession.setCamera(self.camera)
        self.camera.start()
