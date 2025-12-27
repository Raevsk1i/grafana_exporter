# GUI/screens/auto_report_screen.py
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLabel, QLineEdit,
    QComboBox, QDateTimeEdit, QPushButton, QMessageBox,
    QCheckBox, QProgressBar, QHBoxLayout
)
from PyQt6.QtCore import Qt, QDateTime, QThreadPool, QPropertyAnimation, QEasingCurve
from GUI.widgets.animated_toggle import AnimatedToggle
from workers.worker import ProcessingWorker


class AutoReportScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.threadpool = QThreadPool()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setSpacing(20)

        # === Заголовок по центру ===
        title_label = QLabel("Автоотчёт")
        title_label.setObjectName("screenTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)

        # === Форма ===
        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form_layout.setHorizontalSpacing(20)
        form_layout.setVerticalSpacing(16)

        self.fp_combo = QComboBox()
        self.fp_combo.addItems(["VAT", "DZKZ", "BUDGET", "GLA"])
        form_layout.addRow("Код ФП:", self.fp_combo)

        self.test_name = QComboBox()
        self.test_name.addItems(["Поиск максимума", "Подтверждение максимума", "Стабильность"])
        form_layout.addRow("Тест:", self.test_name)

        self.page_id_edit = QLineEdit()
        self.page_id_edit.setPlaceholderText("123456789")
        form_layout.addRow("Page ID:", self.page_id_edit)

        self.page_name_edit = QLineEdit()
        self.page_name_edit.setPlaceholderText("Название страницы")
        form_layout.addRow("Page Name:", self.page_name_edit)

        self.from_datetime = QDateTimeEdit()
        self.from_datetime.setDisplayFormat("dd.MM.yyyy HH:mm")
        self.from_datetime.setCalendarPopup(True)
        self.from_datetime.setDateTime(QDateTime.currentDateTime().addDays(-7))
        form_layout.addRow("From:", self.from_datetime)

        self.to_datetime = QDateTimeEdit()
        self.to_datetime.setDisplayFormat("dd.MM.yyyy HH:mm")
        self.to_datetime.setCalendarPopup(True)
        self.to_datetime.setDateTime(QDateTime.currentDateTime())
        form_layout.addRow("To:", self.to_datetime)

        self.space_edit = QLineEdit()
        self.space_edit.setPlaceholderText("SBERERP_TESTING")
        form_layout.addRow("Пространство Confluence:", self.space_edit)

        self.parent_id_edit = QLineEdit()
        self.parent_id_edit.setPlaceholderText("123456789")
        form_layout.addRow("Parent Page ID:", self.parent_id_edit)

        self.mode_switch = AnimatedToggle(
            bar_color_true="#9333ea",
            bar_color_false="#495057",
            handle_color="#ffffff",
            animation_duration=150,
            animation_curve="OutCubic",
        )
        self.mode_switch.setChecked(False)
        self.mode_switch.stateChanged.connect(self.on_mode_changed)
        form_layout.addRow("Append mode:", self.mode_switch)

        self.music_checkbox = QCheckBox("Включить фоновую музыку")
        form_layout.addRow("", self.music_checkbox)

        main_layout.addLayout(form_layout)
        main_layout.addStretch()

        # Для запуска и back
        bottom_layout = QHBoxLayout()

        # Кнопка запуска
        self.run_button = QPushButton("Запустить")
        self.run_button.setObjectName("runButton")
        self.run_button.clicked.connect(self.on_run_clicked)

        bottom_layout.addWidget(self.run_button)

        # Кнопка Назад справа
        self.back_button = QPushButton("← Назад")
        self.back_button.setObjectName("backButton")
        self.back_button.setFixedWidth(80)
        self.back_button.clicked.connect(self.go_back)

        bottom_layout.addWidget(self.back_button)

        main_layout.addLayout(bottom_layout)

        # Прогресс-бар
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setTextVisible(False)
        self.progress_bar.hide()
        main_layout.addWidget(self.progress_bar)

        self.progress_animation = QPropertyAnimation(self.progress_bar, b"value")
        self.progress_animation.setDuration(500)
        self.progress_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Инициализация состояния
        self.on_mode_changed()

    def go_back(self):
        if self.parent_window and hasattr(self.parent_window, "stacked_widget"):
            self.parent_window.stacked_widget.setCurrentIndex(0)

    def on_mode_changed(self):
        append_mode = self.mode_switch.isChecked()
        if append_mode:
            self.parent_id_edit.setDisabled(True)
            self.parent_id_edit.clear()
            self.space_edit.setDisabled(True)
            self.space_edit.clear()
            self.page_id_edit.setEnabled(True)
        else:
            self.page_id_edit.setDisabled(True)
            self.page_id_edit.clear()
            self.parent_id_edit.setEnabled(True)
            self.space_edit.setEnabled(True)

    def get_parameters(self):
        return {
            "fp_code": self.fp_combo.currentText(),
            "page_id": self.page_id_edit.text().strip(),
            "page_name": self.page_name_edit.text().strip(),
            "from_dt": self.from_datetime.dateTime().toString("dd.MM.yyyy HH:mm"),
            "to_dt": self.to_datetime.dateTime().toString("dd.MM.yyyy HH:mm"),
            "space": self.space_edit.text().strip(),
            "parent_id": self.parent_id_edit.text().strip(),
            "append_mode": self.mode_switch.isChecked(),
            "background_music": self.music_checkbox.isChecked()
        }

    def update_progress(self, value: int):
        self.progress_animation.stop()
        self.progress_animation.setStartValue(self.progress_bar.value())
        self.progress_animation.setEndValue(value)
        self.progress_animation.start()

    def on_run_clicked(self):
        params = self.get_parameters()

        # Валидация
        if self.parent_id_edit.isEnabled():
            if params["append_mode"] and (not params["parent_id"].isdigit() or not params["space"]):
                QMessageBox.warning(self, "Внимание", "При создании страницы укажите Parent Page ID и Пространство.")
                return
            if not params["page_name"]:
                QMessageBox.warning(self, "Внимание", "Введите Page Name.")
                return
        else:
            if not params["append_mode"] and not params["page_id"].isdigit():
                QMessageBox.warning(self, "Внимание", "Page ID должен содержать только цифры.")
                return

        self.run_button.setDisabled(True)
        self.run_button.setText("Обработка...")
        self.progress_bar.show()
        self.progress_bar.setValue(0)

        worker = ProcessingWorker(params, self.progress_bar)
        worker.signals.finished.connect(self.on_finished)
        worker.signals.error.connect(self.on_error)
        worker.signals.progress.connect(self.update_progress)

        self.threadpool.start(worker)

    def on_finished(self):
        self.run_button.setEnabled(True)
        self.run_button.setText("Запустить")
        QMessageBox.information(self, "Успех", "Обработка завершена успешно!")

    def on_error(self, trace):
        self.run_button.setEnabled(True)
        self.run_button.setText("Запустить")
        QMessageBox.critical(self, "Ошибка", f"Произошла ошибка:\n{trace}")