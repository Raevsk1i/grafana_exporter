from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QVBoxLayout, QLabel, QHBoxLayout, QWidget, QPushButton


class ReflexTransferScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        # Заголовок
        title = QLabel("Reflex-transfer")
        title.setObjectName("screenTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Основной текст
        info = QLabel("<p style='font-size: 14pt; color: #bbbbbb;'>Функционал в разработке...</p>")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info.setWordWrap(True)
        layout.addWidget(info)

        layout.addStretch()

        # Нижняя панель с кнопкой Назад в правом углу
        bottom_bar = QHBoxLayout()
        bottom_bar.addStretch()

        back_button = QPushButton("← Назад")
        back_button.setObjectName("backButton")
        back_button.setFixedWidth(140)
        back_button.clicked.connect(self.go_back)
        bottom_bar.addWidget(back_button)

        layout.addLayout(bottom_bar)

    def go_back(self):
        if self.parent_window:
            self.parent_window.stacked_widget.setCurrentIndex(0)