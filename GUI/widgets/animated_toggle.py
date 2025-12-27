# widgets/animated_toggle.py
from PyQt6.QtCore import Qt, QPropertyAnimation, QSize, QPointF, QRectF, pyqtProperty
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen
from PyQt6.QtWidgets import QCheckBox, QSizePolicy


class AnimatedToggle(QCheckBox):
    def __init__(
        self,
        parent=None,
        bar_color_true="#660066",      # зелёный, когда включено
        bar_color_false="#495057",     # серый, когда выключено
        handle_color="#ffffff",
        animation_curve="OutCubic",
        animation_duration=150,
    ):
        super().__init__(parent)

        # Настройки
        self._bar_color_true = QColor(bar_color_true)
        self._bar_color_false = QColor(bar_color_false)
        self._handle_color = QColor(handle_color)

        self._animation_duration = animation_duration
        self._animation_curve = animation_curve

        # Размеры
        self.setContentsMargins(8, 0, 8, 0)
        self.setFixedSize(54 + 24, 28)  # ширина дорожки + запас + ширина ручки

        # Анимация
        self._handle_position = 0.0
        self._animation = QPropertyAnimation(self, b"handle_position", self)
        self._animation.setDuration(self._animation_duration)
        # self._animation.setEasingCurve(animation_curve)

        # Подключение изменения состояния
        self.stateChanged.connect(self.start_transition)

    @pyqtProperty(float)
    def handle_position(self):
        return self._handle_position

    @handle_position.setter
    def handle_position(self, value):
        self._handle_position = value
        self.update()  # перерисовка

    def start_transition(self):
        if self.isChecked():
            self._animation.setStartValue(0.0)
            self._animation.setEndValue(1.0)
        else:
            self._animation.setStartValue(1.0)
            self._animation.setEndValue(0.0)
        self._animation.start()

    def sizeHint(self):
        return QSize(78, 28)  # немного шире, чтобы текст помещался, если нужен

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        bar_rect = QRectF(0, (rect.height() - 28) / 2, 54, 28)
        handle_rect = QRectF(0, (rect.height() - 24) / 2, 24, 24)

        # Позиция ручки
        handle_x = bar_rect.x() + self._handle_position * (bar_rect.width() - handle_rect.width())
        handle_center = QPointF(handle_x + handle_rect.width() / 2, bar_rect.center().y())

        # Отрисовка дорожки (фона)
        painter.setPen(Qt.PenStyle.NoPen)
        if self.isChecked():
            painter.setBrush(QBrush(self._bar_color_true))
        else:
            painter.setBrush(QBrush(self._bar_color_false))
        painter.drawRoundedRect(bar_rect, 14, 14)

        # Отрисовка ручки
        painter.setBrush(QBrush(self._handle_color))
        painter.setPen(QPen(QColor("#343a40"), 1))  # лёгкая обводка для контраста
        painter.drawEllipse(handle_center, 12, 12)  # радиус 12 -> диаметр 24

        painter.end()