from atlassian import Confluence
from typing import List, Dict
from pathlib import Path
from config import ConfigManager
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class ConfluenceAttachmentService:
    """Service for managing Confluence attachments (upload, list, delete)."""

    def __init__(self, config: ConfigManager):
        self.confluence = Confluence(
            url=config.get_value('Confluence_url'),
            token=config.get_value('Confluence_api_token'),
            verify_ssl=False
        )

    def upload_attachments(self, graphics: Dict[str, Dict[str, str]], page_id: str) -> bool:
        """Uploads all graphics as attachments to a page."""
        try:
            for container_graphics in graphics.values():
                for screenshot_path in container_graphics.values():
                    self.confluence.attach_file(screenshot_path, page_id=page_id)
            return True
        except Exception as error:
            logger.error(f"Error uploading attachments: {error}")
            return False

    def get_page_attachments(self, page_id: str) -> List[Dict]:
        """Gets list of attachments for a page."""
        try:
            attachments = self.confluence.get_attachments_from_content(page_id)
            return attachments.get('results', [])
        except Exception as error:
            logger.error(f"Error getting attachments: {error}")
            return []

    def delete_attachment(self, page_id: str, filename: str) -> bool:
        """Deletes an attachment from a page."""
        try:
            self.confluence.delete_attachment(page_id, filename)
            return True
        except Exception as error:
            logger.error(f"Error deleting attachment {filename}: {error}")
            return False