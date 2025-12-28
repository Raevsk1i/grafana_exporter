import time

from PyQt6.QtCore import QRunnable, pyqtSlot, QObject, pyqtSignal


# Бедный работяга
class ReflexWorker(QRunnable):
    def __init__(self, func, action_name: str, *args):
        super().__init__()
        self.func = func
        self.action_name = action_name
        self.args = args
        self.signals = ReflexWorkerSignals()

    @pyqtSlot()
    def run(self):
        try:
            response = self.func(*self.args)
            self.signals.success.emit(self.action_name, response)
        except Exception as e:
            self.signals.error.emit(self.action_name, str(e))


class ReflexWorkerSignals(QObject):
    success = pyqtSignal(str, dict)   # название действия, ответ
    error = pyqtSignal(str, str)      # название действия, ошибка