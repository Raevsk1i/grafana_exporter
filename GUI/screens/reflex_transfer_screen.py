from PyQt6.QtCore import Qt, QThreadPool, QDateTime, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QVBoxLayout, QLabel, QHBoxLayout, QWidget, QPushButton, QMessageBox, QGridLayout, \
    QInputDialog, QLineEdit, QDialogButtonBox, QTextEdit, QDialog, QFormLayout, QDateTimeEdit

import json
from config import config
from service.reflex_transfer_service import reflex_service
from workers.reflex_worker import ReflexWorker


# --- Диалог для показа JSON-ответа ---
class JsonResponseDialog(QDialog):
    def __init__(self, title: str, response: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(800, 600)

        layout = QVBoxLayout(self)

        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setFont(QFont("Consolas", 11))

        try:
            pretty_json = json.dumps(response, indent=2, ensure_ascii=False)
        except:
            pretty_json = str(response)

        text_edit.setPlainText(pretty_json)
        layout.addWidget(text_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)


# --- Диалог для "Трансфер From-To" с QDateTimeEdit ---
class TransferFromToDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Трансфер From-To")
        self.resize(400, 250)

        layout = QFormLayout(self)

        self.fp_code_edit = QLineEdit()
        self.fp_code_edit.setPlaceholderText("VAT, BUDGET и т.д.")

        self.from_dt = QDateTimeEdit()
        self.from_dt.setCalendarPopup(True)
        self.from_dt.setDisplayFormat("dd.MM.yyyy HH:mm")
        self.from_dt.setDateTime(QDateTime.currentDateTime().addDays(-7))

        self.to_dt = QDateTimeEdit()
        self.to_dt.setCalendarPopup(True)
        self.to_dt.setDisplayFormat("dd.MM.yyyy HH:mm")
        self.to_dt.setDateTime(QDateTime.currentDateTime())

        layout.addRow("КОД ФП:", self.fp_code_edit)
        layout.addRow("From:", self.from_dt)
        layout.addRow("To:", self.to_dt)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_values(self):
        fp_code = self.fp_code_edit.text().strip()

        # Получаем QDateTime из виджетов
        from_qdt = self.from_dt.dateTime()
        to_qdt = self.to_dt.dateTime()

        # Преобразуем в Unix timestamp в миллисекундах (UTC!)
        from_ms = int(from_qdt.toMSecsSinceEpoch())
        to_ms = int(to_qdt.toMSecsSinceEpoch())

        return fp_code, from_ms, to_ms

# Screen с кнопками для взаимодействия с приложением reflex-transfer
class ReflexTransferScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.threadpool = QThreadPool()
        self.buttons = {}

        self.dot_count = 0  # Текущее количество точек
        self.loading_timer = QTimer(self)
        self.loading_timer.timeout.connect(self.update_loading_dots)

        self.current_action_name = ""  # Запоминаем название действия для анимации

        self.build_ui()

        if not config.get_value('reflex_transfer_url').strip():
            self.prompt_for_url()
        else:
            self.enable_action_buttons()

    # Собрать UI
    def build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setSpacing(30)

        # Заголовок
        title = QLabel("Reflex Transfer")
        title.setObjectName("screenTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title)

        # Статусная строка
        self.status_label = QLabel("Выберите действие")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: #bbbbbb; font-size: 14pt;")
        main_layout.addWidget(self.status_label)

        # === Группа REFLEX ===
        reflex_group = QLabel("<b>REFLEX</b>")
        reflex_group.setStyleSheet("font-size: 16pt; color: #ffffff;")
        reflex_group.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(reflex_group)

        reflex_grid = QGridLayout()
        reflex_grid.setSpacing(15)

        reflex_buttons = [
            ("Создать трансфер", self.create_regular_transfer_action),
            ("Трансфер From-To", self.create_transfer_from_to_action),
            ("Удалить трансфер", self.stop_regular_transfer_action),
            ("Получить все активные трансферы", self.get_all_transfers_action),
        ]

        for i, (text, callback) in enumerate(reflex_buttons):
            btn = QPushButton(text)
            btn.setObjectName("reflexActionButton")
            btn.setFixedHeight(60)
            btn.setFont(QFont("", 12, QFont.Weight.Bold))
            btn.clicked.connect(callback)
            self.buttons[text] = btn if hasattr(self, 'buttons') else {}
            self.buttons.setdefault(text, btn)
            reflex_grid.addWidget(btn, i // 2, i % 2)

        reflex_wrapper = QHBoxLayout()
        reflex_wrapper.addStretch()
        reflex_wrapper.addLayout(reflex_grid)
        reflex_wrapper.addStretch()
        main_layout.addLayout(reflex_wrapper)

        # === Группа INFLUX ===
        influx_group = QLabel("<b>INFLUX</b>")
        influx_group.setStyleSheet("font-size: 16pt; color: #ffffff;")
        influx_group.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(influx_group)

        influx_grid = QGridLayout()
        influx_grid.setSpacing(15)

        influx_buttons = [
            # ("Удалить инстансы ФП", self.delete_instances_action), # Требуется добавить эту функцию в reflex-transfer
            ("Пересоздать базу данных", self.recreate_db_action),
        ]

        for i, (text, callback) in enumerate(influx_buttons):
            btn = QPushButton(text)
            btn.setObjectName("reflexActionButton")
            btn.setFixedHeight(60)
            btn.setFont(QFont("", 12, QFont.Weight.Bold))
            btn.clicked.connect(callback)
            self.buttons[text] = btn
            influx_grid.addWidget(btn, i // 2, i % 2)

        influx_wrapper = QHBoxLayout()
        influx_wrapper.addStretch()
        influx_wrapper.addLayout(influx_grid)
        influx_wrapper.addStretch()
        main_layout.addLayout(influx_wrapper)

        main_layout.addStretch()

        # Кнопка Назад
        bottom_bar = QHBoxLayout()
        bottom_bar.addStretch()

        back_button = QPushButton("← Назад")
        back_button.setObjectName("backButton")
        back_button.setFixedWidth(140)
        back_button.clicked.connect(self.go_back)
        bottom_bar.addWidget(back_button)

        main_layout.addLayout(bottom_bar)
        main_layout.addSpacing(20)

    # Выскакивает в случае, когда reflex_url не указан
    def prompt_for_url(self):
        self.loading_timer.stop()  # На всякий случай
        self.disable_action_buttons()
        self.status_label.setText("<span style='color: #ff6b6b;'>URL не указан. Введите его:</span>")

        url, ok = QInputDialog.getText(
            self, "Настройка", "Базовый URL Reflex Transfer API:",
            QLineEdit.EchoMode.Normal, config.get_value('reflex_transfer_url').strip() or "https://"
        )

        if ok and url.strip():
            config.set_value("reflex_transfer_url", url.strip())
            QMessageBox.information(self, "Готово", "URL сохранён.")
            self.status_label.setText("Выберите действие")
            self.enable_action_buttons()
        elif ok:
            QMessageBox.warning(self, "Ошибка", "URL обязателен!")
            self.prompt_for_url()
        else:
            self.go_back()

    # Включает кнопки
    def enable_action_buttons(self):
        for btn in self.buttons.values():
            btn.setEnabled(True)

    # Отключает кнопки
    def disable_action_buttons(self):
        for btn in self.buttons.values():
            btn.setEnabled(False)

    # Служит для имитации прогресса после нажатия на кнопку
    def update_loading_dots(self):
        self.dot_count = (self.dot_count + 1) % 4  # 0, 1, 2, 3 → "", ".", "..", "..."
        dots = "." * self.dot_count
        self.status_label.setText(f"Выполняется: {self.current_action_name}{dots}")

    # Запускает основную логику и делит на поток
    def run_action(self, func, action_name: str, *args):
        self.disable_action_buttons()

        # Запоминаем действие и запускаем анимацию точек
        self.current_action_name = action_name
        self.dot_count = 0
        self.status_label.setText(f"Выполняется: {action_name}")
        self.loading_timer.start(400)  # Обновляем каждые 400 мс

        worker = ReflexWorker(func, action_name, *args)
        worker.signals.success.connect(self.on_success)
        worker.signals.error.connect(self.on_error)
        self.threadpool.start(worker)

    # В случае отправки запроса
    def on_success(self, action_name: str, response: dict):
        self.loading_timer.stop()  # Останавливаем точки
        self.enable_action_buttons()
        self.status_label.setText("Выберите действие")

        if action_name == "Получить все активные трансферы":
            JsonResponseDialog("Активные трансферы", response, self).exec()
        else:
            QMessageBox.information(
                self, "Успех",
                f"<b>{action_name}</b><br><br>Успешно выполнено.<br><pre>{json.dumps(response, indent=2, ensure_ascii=False)}</pre>"
            )

    # В случае какой-то ошибки во время попытки отправить запрос
    def on_error(self, action_name: str, error_msg: str):
        self.loading_timer.stop()  # Останавливаем точки
        self.enable_action_buttons()
        self.status_label.setText("Выберите действие")
        QMessageBox.critical(self, "Ошибка", f"<b>{action_name}</b><br><br>{error_msg}")

    # === Методы сервиса reflex_transfer_service === Требуется изменить для правильной работы
    def create_regular_transfer_action(self):
        fp_code, ok = QInputDialog.getText(self, "Создать трансфер", "Введите КОД ФП:")
        if ok and fp_code.strip():
            self.run_action(reflex_service.send_create_transfer_request,
                            "Создать трансфер",
                            fp_code)
        elif ok:
            QMessageBox.warning(self, "Ошибка", "Код ФП обязателен")

    def create_transfer_from_to_action(self):
        dialog = TransferFromToDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            fp_code, from_ms, to_ms = dialog.get_values()
            if not fp_code:
                QMessageBox.warning(self, "Ошибка", "Код ФП обязателен")
                return
            self.run_action(
                reflex_service.send_start_transfer_from_to_request,
                "Трансфер From-To",
                fp_code, from_ms, to_ms
            )

    def stop_regular_transfer_action(self):
        fp_code, ok = QInputDialog.getText(self, "Остановить трансфер", "Введите КОД ФП:")
        if ok and fp_code.strip():
            self.run_action(reflex_service.send_stop_transfer_request,
                            "Остановить трансфер",
                            fp_code)
        elif ok:
            QMessageBox.warning(self, "Ошибка", "Код ФП обязателен")

    def get_all_transfers_action(self):
        self.run_action(reflex_service.send_get_transfers_request,
                        "Получить все активные трансферы")

    def delete_instances_action(self):
        fp_code, ok = QInputDialog.getText(self, "Удалить инстансы ФП", "Введите КОД ФП:")
        if ok and fp_code.strip():
            reply = QMessageBox.question(self, "Подтверждение", f"Удалить инстансы для {fp_code}?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.run_action(reflex_service.send_delete_instance_request,
                                "Удалить инстансы ФП",
                                fp_code)
        elif ok:
            QMessageBox.warning(self, "Ошибка", "Код ФП обязателен")

    def recreate_db_action(self):
        reply = QMessageBox.question(self, "Подтверждение", "Пересоздать базу данных?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.run_action(reflex_service.send_recreate_database_request,
                            "Пересоздать базу данных")

    # Возврат на главное меню
    def go_back(self):
        if self.parent_window:
            self.parent_window.stacked_widget.setCurrentIndex(0)