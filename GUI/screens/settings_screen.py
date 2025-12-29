# GUI/screens/settings_screen.py

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QHBoxLayout, QFormLayout, QMessageBox,
    QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import Qt
from config import config


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

        # Две колонки
        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(40)

        # Левая колонка
        left_form = QFormLayout()
        left_form.setHorizontalSpacing(20)
        left_form.setVerticalSpacing(16)
        left_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # Правая колонка
        right_form = QFormLayout()
        right_form.setHorizontalSpacing(20)
        right_form.setVerticalSpacing(16)
        right_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        left_params = {
            "Grafana_host": "Grafana Host",
            "Grafana_port": "Grafana Port",
            "Grafana_api_token": "Grafana API Token",
            "Grafana_dashboard_uid": "Grafana Dashboard UID",
            "Grafana_dashboard_slug": "Grafana Dashboard Slug",
            "Grafana_max_workers": "Grafana Max Workers",
            "Grafana_request_delay": "Grafana Request Delay (сек)",
            "Grafana_max_retries": "Grafana Max Retries",
            "reflex_transfer_url": "Reflex Transfer URL",
        }

        right_params = {
            "Confluence_url": "Confluence URL",
            "Confluence_api_token": "Confluence API Token",
            "Confluence_username": "Confluence Username",
            "Influxdb_url": "InfluxDB URL",
            "Influxdb_port": "InfluxDB Port",
            "Influxdb_username": "InfluxDB Username",
            "Influxdb_password": "InfluxDB Password",
            "Influxdb_database": "InfluxDB Database",
        }

        self.edit_widgets = {}

        # Заполняем левую колонку
        for key, label_text in left_params.items():
            self._add_field(left_form, key, label_text)

        # Заполняем правую колонку
        for key, label_text in right_params.items():
            is_password = key == "Influxdb_password"
            self._add_field(right_form, key, label_text, is_password=is_password)

        columns_layout.addLayout(left_form)
        columns_layout.addLayout(right_form)
        columns_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        layout.addLayout(columns_layout)

        # Кнопка сброса
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

    def _add_field(self, form_layout: QFormLayout, key: str, label_text: str, is_password: bool = False):
        """Добавляет поле с переносом текста в метке и фиксированной шириной поля ввода"""
        label = QLabel(f"{label_text}:")
        label.setWordWrap(True)                    # Ключевое: перенос текста
        label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        label.setMinimumWidth(180)                 # Ограничиваем ширину метки
        label.setMaximumWidth(220)

        edit = QLineEdit()
        if is_password:
            edit.setEchoMode(QLineEdit.EchoMode.Password)

        edit.setPlaceholderText(f"Введите {label_text.lower()}")
        edit.setMinimumWidth(250)                  # Достаточная ширина поля ввода
        edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        # Загружаем значение из config
        current_value = config.get_value(key, "")
        edit.setText(current_value)

        # Сохраняем при изменении
        edit.textChanged.connect(lambda text, k=key: config.set_value(k, text))

        # Добавляем в форму: метка может занимать несколько строк, поле — справа
        form_layout.addRow(label, edit)
        self.edit_widgets[key] = edit

    def reset_all_settings(self):
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            "Сбросить все настройки до значений по умолчанию?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            for key in self.edit_widgets:
                default = config.defaults.get(key, "")
                config.set_value(key, default)
                self.edit_widgets[key].setText(default)

            QMessageBox.information(self, "Успех", "Настройки сброшены до значений по умолчанию!")

    def go_back(self):
        if self.parent_window:
            self.parent_window.stacked_widget.setCurrentIndex(0)