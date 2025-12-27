# widgets/animated_toggle.py
from PyQt6.QtCore import Qt, QPropertyAnimation, QSize, QPointF, QRectF, pyqtProperty, QEasingCurve
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen
from PyQt6.QtWidgets import QCheckBox

class AnimatedToggle(QCheckBox):
    def __init__(
        self,
        parent=None,
        bar_color_true="#9333ea",
        bar_color_false="#404040",
        handle_color="#ffffff",
        animation_duration=150,
        animation_curve="OutCubic",  # строка — удобно передавать из GUI
    ):
        super().__init__(parent)

        self._bar_color_true = QColor(bar_color_true)
        self._bar_color_false = QColor(bar_color_false)
        self._handle_color = QColor(handle_color)

        self._animation_duration = animation_duration

        # Преобразуем строку в QEasingCurve.Type
        curve_map = {
            "Linear": QEasingCurve.Type.Linear,
            "InQuad": QEasingCurve.Type.InQuad,
            "OutQuad": QEasingCurve.Type.OutQuad,
            "InOutQuad": QEasingCurve.Type.InOutQuad,
            "OutInQuad": QEasingCurve.Type.OutInQuad,
            "InCubic": QEasingCurve.Type.InCubic,
            "OutCubic": QEasingCurve.Type.OutCubic,
            "InOutCubic": QEasingCurve.Type.InOutCubic,
            "OutInCubic": QEasingCurve.Type.OutInCubic,
            "InQuart": QEasingCurve.Type.InQuart,
            "OutQuart": QEasingCurve.Type.OutQuart,
            "InOutQuart": QEasingCurve.Type.InOutQuart,
            "InQuint": QEasingCurve.Type.InQuint,
            "OutQuint": QEasingCurve.Type.OutQuint,
            "InOutQuint": QEasingCurve.Type.InOutQuint,
            "InSine": QEasingCurve.Type.InSine,
            "OutSine": QEasingCurve.Type.OutSine,
            "InOutSine": QEasingCurve.Type.InOutSine,
            "InExpo": QEasingCurve.Type.InExpo,
            "OutExpo": QEasingCurve.Type.OutExpo,
            "InOutExpo": QEasingCurve.Type.InOutExpo,
            "InCirc": QEasingCurve.Type.InCirc,
            "OutCirc": QEasingCurve.Type.OutCirc,
            "InOutCirc": QEasingCurve.Type.InOutCirc,
            "InElastic": QEasingCurve.Type.InElastic,
            "OutElastic": QEasingCurve.Type.OutElastic,
            "InOutElastic": QEasingCurve.Type.InOutElastic,
            "InBack": QEasingCurve.Type.InBack,
            "OutBack": QEasingCurve.Type.OutBack,
            "InOutBack": QEasingCurve.Type.InOutBack,
            "InBounce": QEasingCurve.Type.InBounce,
            "OutBounce": QEasingCurve.Type.OutBounce,
            "InOutBounce": QEasingCurve.Type.InOutBounce,
            "OutInBounce": QEasingCurve.Type.OutInBounce,
        }

        self._easing_type = curve_map.get(animation_curve, QEasingCurve.Type.OutCubic)

        # Размеры
        self.setFixedSize(80, 30)
        self.setContentsMargins(8, 0, 8, 0)

        # Анимация
        self._handle_position = 0.0
        self._animation = QPropertyAnimation(self, b"handle_position", self)
        self._animation.setDuration(self._animation_duration)
        self._animation.setEasingCurve(self._easing_type)  # теперь правильный тип!

        self.stateChanged.connect(self.start_transition)

    # Делаем весь виджет кликабельным
    def hitButton(self, pos):
        return self.contentsRect().contains(pos)

    @pyqtProperty(float)
    def handle_position(self):
        return self._handle_position

    @handle_position.setter
    def handle_position(self, value):
        self._handle_position = value
        self.update()

    def start_transition(self):
        self._animation.stop()
        if self.isChecked():
            self._animation.setStartValue(0.0)
            self._animation.setEndValue(1.0)
        else:
            self._animation.setStartValue(1.0)
            self._animation.setEndValue(0.0)
        self._animation.start()

    def sizeHint(self):
        return QSize(80, 30)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        bar_width = 56
        bar_height = 30
        handle_diameter = 26

        # Центрируем дорожку по вертикали
        bar_rect = QRectF(
            (rect.width() - bar_width) / 2,
            (rect.height() - bar_height) / 2,
            bar_width,
            bar_height
        )

        # Цвет дорожки в зависимости от состояния
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._bar_color_true if self.isChecked() else self._bar_color_false)
        painter.drawRoundedRect(bar_rect, 15, 15)

        # Позиция ручки
        handle_x = bar_rect.x() + 2 + self._handle_position * (bar_width - handle_diameter - 4)
        handle_center = QPointF(handle_x + handle_diameter / 2, bar_rect.center().y())

        # Ручка
        painter.setBrush(QBrush(self._handle_color))
        painter.drawEllipse(handle_center, handle_diameter / 2, handle_diameter / 2)

        painter.end()