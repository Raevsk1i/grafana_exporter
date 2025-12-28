# service/confluence_service.py
from atlassian import Confluence
from config import config
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class ConfluenceService:
    """Единая точка создания и хранения Confluence клиента."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.confluence = Confluence(
            url=config.get_value('Confluence_url'),
            username=config.get_value('Confluence_username'),
            password=config.get_value('Confluence_api_key'),  # или token=
            verify_ssl=False
        )
        self._initialized = True

    def get_client(self):
        return self.confluence