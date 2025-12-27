# GUI/main_gui.py
from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QPushButton, QStackedWidget, QApplication
from PyQt6.QtCore import Qt
import os

from GUI.screens.auto_report_screen import AutoReportScreen
from GUI.screens.reflex_transfer_screen import ReflexTransferScreen
from GUI.screens.settings_screen import SettingsScreen


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LT Tools")
        self.resize(700, 800)

        self.apply_styles()

        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        self.menu_screen = self.create_menu_screen()

        # Передаём self (MainWindow) как parent каждому экрану
        self.auto_report_screen = AutoReportScreen(parent=self)
        self.reflex_screen = ReflexTransferScreen(parent=self)
        self.settings_screen = SettingsScreen(parent=self)

        self.stacked_widget.addWidget(self.menu_screen)
        self.stacked_widget.addWidget(self.auto_report_screen)
        self.stacked_widget.addWidget(self.reflex_screen)
        self.stacked_widget.addWidget(self.settings_screen)

        self.stacked_widget.setCurrentWidget(self.menu_screen)

    def create_menu_screen(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(60, 60, 60, 60)
        layout.setSpacing(30)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QPushButton("LT Tools")
        title.setEnabled(False)
        title.setObjectName("titleButton")
        layout.addWidget(title)

        btn1 = QPushButton("1. Автоотчёт")
        btn1.setObjectName("menuButton")
        btn1.clicked.connect(lambda: self.stacked_widget.setCurrentWidget(self.auto_report_screen))
        layout.addWidget(btn1)

        btn2 = QPushButton("2. Reflex-transfer")
        btn2.setObjectName("menuButton")
        btn2.clicked.connect(lambda: self.stacked_widget.setCurrentWidget(self.reflex_screen))
        layout.addWidget(btn2)

        btn3 = QPushButton("3. Настройки")
        btn3.setObjectName("menuButton")
        btn3.clicked.connect(lambda: self.stacked_widget.setCurrentWidget(self.settings_screen))
        layout.addWidget(btn3)

        layout.addStretch()
        return widget

    def apply_styles(self):
        style_path = os.path.join(os.path.dirname(__file__), "..", "resources", "style.qss")
        if os.path.exists(style_path):
            try:
                with open(style_path, "r", encoding="utf-8") as f:
                    self.setStyleSheet(f.read())
            except Exception as e:
                print(f"Ошибка чтения style.qss: {e}")


# Чтобы можно было запускать напрямую для теста
if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()