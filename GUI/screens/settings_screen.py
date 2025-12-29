# GUI/screens/settings_screen.py
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QHBoxLayout, QFormLayout, QMessageBox
)
from PyQt6.QtCore import Qt
from config import config  # Импортируем глобальный config


# Окно с настройками констант, которые шарятся на все приложение
class SettingsScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        # Заголовок
        title = QLabel("Настройки")
        title.setObjectName("screenTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Список параметров-констант названиями
        self.param_fields = {
            "Grafana_host": "Grafana Host",
            "Grafana_port": "Grafana Port",
            "Grafana_api_token": "Grafana API Token",
            "Grafana_dashboard": "Grafana Dashboard UID",
            "Grafana_param5": "Доп. параметр Grafana",
            "Confluence_url": "Confluence URL",
            "Confluence_api_token": "Confluence API Token",
            "Confluence_username": "Confluence Username",
            "Confluence_param9": "Доп. параметр Confluence 2",
            "reflex_transfer_url": "Reflex Transfer URL",
        }

        form_layout = QFormLayout()
        form_layout.setHorizontalSpacing(20)
        form_layout.setVerticalSpacing(16)

        self.edit_widgets = {}  # Для сброса

        for key, label_text in self.param_fields.items():
            label = QLabel(f"{label_text}:")
            edit = QLineEdit()
            edit.setPlaceholderText(f"Введите {label_text.lower()}")

            # Загружаем текущее значение из config
            current_value = config.get_value(key, "")
            edit.setText(current_value)

            # При изменении — сохраняем в config
            edit.textChanged.connect(
                lambda text, k=key: config.set_value(k, text)
            )

            form_layout.addRow(label, edit)
            self.edit_widgets[key] = edit

        layout.addLayout(form_layout)

        # Кнопка сброса: Сбрасывает все параметры
        reset_button = QPushButton("Сбросить все настройки")
        reset_button.setObjectName("resetButton")
        reset_button.clicked.connect(self.reset_all_settings)
        layout.addWidget(reset_button, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addStretch()

        # Кнопка Назад
        bottom_bar = QHBoxLayout()
        bottom_bar.addStretch()

        back_button = QPushButton("← Назад")
        back_button.setObjectName("backButton")
        back_button.setFixedWidth(140)
        back_button.clicked.connect(self.go_back)
        bottom_bar.addWidget(back_button)

        layout.addLayout(bottom_bar)
        layout.addSpacing(20)

    def reset_all_settings(self):
        reply = QMessageBox.question(
            self, "Подтверждение",
            "Сбросить все настройки до значений по умолчанию?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Сбрасываем в config (он сам сохранит в QSettings)
            for key in self.param_fields.keys():
                default = config.defaults.get(key, "")
                config.set_value(key, default)
                self.edit_widgets[key].setText(default)

            QMessageBox.information(self, "Успех", "Настройки сброшены до значений по умолчанию!")

    def go_back(self):
        if self.parent_window:
            self.parent_window.stacked_widget.setCurrentIndex(0)