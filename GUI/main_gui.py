# main_gui.py
import os
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QGridLayout, QFormLayout,
    QLabel, QLineEdit, QComboBox, QDateTimeEdit, QPushButton,
    QMessageBox, QCheckBox, QApplication, QProgressBar
)
from GUI.widgets.animated_toggle import AnimatedToggle
from PyQt6.QtCore import Qt, QDateTime, QThreadPool, QPropertyAnimation, QEasingCurve
from workers.worker import ProcessingWorker


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Confluence Page Processor")
        self.resize(600, 750)

        self.apply_styles()

        self.threadpool = QThreadPool()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setSpacing(20)

        # Форма с полями
        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form_layout.setFormAlignment(Qt.AlignmentFlag.AlignLeft)
        form_layout.setHorizontalSpacing(20)
        form_layout.setVerticalSpacing(16)

        # Параметр 1: Код ФП
        self.fp_combo = QComboBox()
        self.fp_combo.addItems(["VAT", "DZKZ", "BUDGET", "GLA"])
        form_layout.addRow("Код ФП:", self.fp_combo)

        # Параметр 2: Название теста
        self.test_name = QComboBox()
        self.test_name.addItems(["Поиск максимума", "Подтверждение максимума", "Стабильность"])
        form_layout.addRow("Тест:", self.test_name)

        # Параметр 3: Page ID
        self.page_id_edit = QLineEdit()
        self.page_id_edit.setPlaceholderText("123456789")
        form_layout.addRow("Page ID:", self.page_id_edit)

        # Параметр 4: Page Name
        self.page_name_edit = QLineEdit()
        self.page_name_edit.setPlaceholderText("Название страницы")
        form_layout.addRow("Page Name:", self.page_name_edit)

        # Параметр 5: From
        self.from_datetime = QDateTimeEdit()
        self.from_datetime.setDisplayFormat("dd.MM.yyyy HH:mm")
        self.from_datetime.setCalendarPopup(True)
        self.from_datetime.setDateTime(QDateTime.currentDateTime().addDays(-7))
        form_layout.addRow("From:", self.from_datetime)

        # Параметр 6: To
        self.to_datetime = QDateTimeEdit()
        self.to_datetime.setDisplayFormat("dd.MM.yyyy HH:mm")
        self.to_datetime.setCalendarPopup(True)
        self.to_datetime.setDateTime(QDateTime.currentDateTime())
        form_layout.addRow("To:", self.to_datetime)

        # Параметр 7: Пространство Confluence
        self.space_edit = QLineEdit()
        self.space_edit.setPlaceholderText("SBERERP")
        form_layout.addRow("Пространство Confluence:", self.space_edit)

        # Параметр 8: Parent Page ID
        self.parent_id_edit = QLineEdit()
        self.parent_id_edit.setPlaceholderText("123456789")
        form_layout.addRow("Parent Page ID:", self.parent_id_edit)

        # Параметр 9: Режим — Добавить / Создать
        self.mode_switch = AnimatedToggle(
            self,
            bar_color_true="#9333ea",
            bar_color_false="#495057",
            handle_color="#ffffff",
            animation_duration=150,
            animation_curve="OutCubic",
        )
        self.mode_switch.setObjectName("modeSwitch")
        self.mode_switch.setChecked(False)
        self.mode_switch.stateChanged.connect(self.on_mode_changed)
        form_layout.addRow("Append mode:", self.mode_switch)

        # Параметр 10: Фоновая музыка
        self.music_checkbox = QCheckBox("Включить фоновую музыку")
        form_layout.addRow("", self.music_checkbox)  # пустая метка для выравнивания

        main_layout.addLayout(form_layout)
        main_layout.addStretch()

        # Кнопка запуска
        self.run_button = QPushButton("Запустить")
        self.run_button.setObjectName("runButton")
        self.run_button.clicked.connect(self.on_run_clicked)
        main_layout.addWidget(self.run_button, alignment=Qt.AlignmentFlag.AlignCenter)

        # Прогресс бар (скрыт по умолчанию)
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setContentsMargins(40, 10, 40, 10)
        self.progress_bar.hide()

        # Анимация для плавного изменения значения
        self.progress_animation = QPropertyAnimation(self.progress_bar, b"value", self)
        self.progress_animation.setDuration(500)  # 500 мс — плавно, но не слишком медленно
        self.progress_animation.setEasingCurve(QEasingCurve.Type.OutCubic)  # красивая кривая (можно InOutQuad и т.д.)

        main_layout.addWidget(self.progress_bar)

        # Инициализация состояния полей
        self.on_mode_changed()

    def apply_styles(self):
        style_path = os.path.join(os.path.dirname("main.py"), "resources", "style.qss")
        if os.path.exists(style_path):
            try:
                with open(style_path, "r", encoding="utf-8") as f:
                    self.setStyleSheet(f.read())
            except Exception as e:
                print(f"Ошибка чтения style.qss: {e}")
        else:
            print(f"style.qss не найден: {style_path}")

    def on_mode_changed(self):
        append_mode = self.mode_switch.isChecked()

        if append_mode:
            # Режим "Создать" — Page ID отключается
            self.parent_id_edit.setDisabled(True)
            self.parent_id_edit.clear()
            self.space_edit.setDisabled(True)
            self.space_edit.clear()
            # Page ID активен
            self.page_id_edit.setEnabled(True)
        else:
            # Режим "Добавить" — отключаем Parent ID и Пространство
            self.page_id_edit.setDisabled(True)
            self.page_id_edit.clear()
            # Остальные поля активны
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
        """Плавно анимирует прогресс-бар до нового значения"""
        self.progress_animation.stop()  # прерываем предыдущую анимацию, если она идёт
        self.progress_animation.setStartValue(self.progress_bar.value())
        self.progress_animation.setEndValue(value)
        self.progress_animation.start()

    def on_run_clicked(self):
        params = self.get_parameters()

        if self.parent_id_edit.isEnabled():
            if params["append_mode"] and (not params["parent_id"].isdigit() or not params["space"]):
                QMessageBox.warning(self, "Внимание",
                                    "При создании страницы укажите Parent Page ID (цифры) и Пространство.")
                return
            if not params["page_name"]:
                QMessageBox.warning(self, "Внимание", "Введите Page Name.")
                return
        else:
            if not params["append_mode"] and not params["page_id"].isdigit():
                QMessageBox.warning(self, "Внимание", "Page ID должен содержать только цифры.")
                return

        # Отключаем кнопку
        self.run_button.setDisabled(True)
        self.run_button.setText("Обработка...")

        # Запускаем воркер
        worker = ProcessingWorker(params, self.progress_bar)
        worker.signals.finished.connect(self.on_processing_finished)
        worker.signals.error.connect(self.on_processing_error)
        worker.signals.progress.connect(self.update_progress)  # <-- вот сюда плавное обновление

        self.progress_bar.show()
        self.progress_bar.setValue(0)  # сброс на начало

        self.threadpool.start(worker)


    def on_processing_finished(self):
        self.run_button.setEnabled(True)
        self.run_button.setText("Запустить")
        QMessageBox.information(self, "Успех", "Обработка завершена успешно!")

    def on_processing_error(self, error_trace):
        self.run_button.setEnabled(True)
        self.run_button.setText("Запустить")
        QMessageBox.critical(self, "Ошибка", f"Произошла ошибка:\n{error_trace}")