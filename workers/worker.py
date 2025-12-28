# workers/worker.py
from PyQt6.QtCore import QRunnable, pyqtSlot, pyqtSignal, QObject
import traceback
import time

from PyQt6.QtWidgets import QProgressBar


class WorkerSignals(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(str)
    result = pyqtSignal(object)
    progress = pyqtSignal(int)

class ProcessingWorker(QRunnable):
    def __init__(self, params: dict, progress_bar: QProgressBar):
        super().__init__()
        self.params = params
        self.signals = WorkerSignals()
        self.progress_bar = progress_bar

    @pyqtSlot()
    def run(self):
        try:
            print("Запуск обработки с параметрами:")
            for key, value in self.params.items():
                print(f"  {key}: {value}")

            # Имитация работы с прогрессом (заменить на реальную логику)

            time.sleep(0.8)
            progress = int(14)
            self.signals.progress.emit(progress)
            time.sleep(0.8)
            progress = int(35)
            self.signals.progress.emit(progress)
            time.sleep(0.8)
            progress = int(67)
            self.signals.progress.emit(progress)
            time.sleep(0.8)
            progress = int(89)
            self.signals.progress.emit(progress)
            time.sleep(0.8)
            progress = int(100)
            self.signals.progress.emit(progress)
            time.sleep(0.8)
            self.signals.finished.emit()

        except Exception as e:
            error_trace = traceback.format_exc()
            print("Ошибка в воркере:", error_trace)
            self.signals.error.emit(error_trace)

        finally:
            self.progress_bar.hide()