# ./service/confluence_service.py
from pathlib import Path
from atlassian import Confluence
from config import config

import logging
import urllib3


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class ConfluenceService:
    def __init__(self):
        self.confluence = Confluence(
            url=config.get_value('Confluence_url'),
            username=config.get_value('Confluence_username'),
            token=config.get_value('Confluence_api_key'),
            verify_ssl=False
        )

    def _load_template(self, test_name) -> str:
        path = f'./resources/test_templates/{test_name}.txt'
        if not Path(path).exists():
            raise FileNotFoundError(f"Шаблон по пути: \"{path}\" не найден")

        with open(path, "r", encoding="utf-8") as template:
            return template.read()

    def _create_page(self, space, title, body):
            page = self.confluence.create_page(space, title, body)
            logger.info(f"{page}")

    # def _upload_attachments(self, attachments: ):





