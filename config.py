# config.py
from PyQt6.QtCore import QSettings, QObject, pyqtSignal

class ConfigManager(QObject):
    """
    Глобальный менеджер конфигурации.
    Хранит все настройки и уведомляет об изменениях.
    """
    # Сигнал, который испускается при изменении любого параметра
    config_changed = pyqtSignal(str, str)  # ключ, новое значение

    def __init__(self):
        super().__init__()
        self.settings = QSettings("ConfluenceTools", "ConfluenceProcessor")

        # Значения по умолчанию (можно изменить)
        self.defaults = {
            "Grafana_host": "http://localhost",
            "Grafana_port": "3000",
            "Grafana_api_token": "",
            "Grafana_dashboard": "default-dashboard",
            "Grafana_param5": "",
            "Confluence_url": "https://your-company.atlassian.net",
            "Confluence_api_token": "",
            "Confluence_username": "",
            "Confluence_param9": "",
            "reflex_transfer_url": "https://api.example.com/reflex-transfer",
        }

        # Загружаем значения из QSettings или используем дефолтные
        for key, default in self.defaults.items():
            value = self.settings.value(key, default, type=str)
            setattr(self, key, value)

    def set_value(self, key: str, value: str):
        """Устанавливает значение и сохраняет в QSettings"""
        if getattr(self, key, None) != value:
            setattr(self, key, value)
            self.settings.setValue(key, value)
            self.settings.sync()
            self.config_changed.emit(key, value)

    def get_value(self, key: str, default: str = "") -> str:
        """Получает значение (с fallback на дефолт)"""
        return getattr(self, key, default)

# Глобальный экземпляр — доступен из любой точки приложения
config = ConfigManager()