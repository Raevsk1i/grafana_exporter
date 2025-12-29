import os
from atlassian import Confluence
from typing import List, Dict
from config import ConfigManager
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class ConfluencePageService:
    """Service for managing Confluence pages (create, update, delete, check existence)."""

    def __init__(self, config: ConfigManager):
        self.confluence = Confluence(
            url=config.get_value('Confluence_url'),
            token=config.get_value('Confluence_api_token'),
            verify_ssl=False
        )

    def create_new_page(self, space: str, title: str, parent_id: str = None) -> str:
        """Creates a new page in Confluence."""
        try:
            result = self.confluence.create_page(
                space=space,
                title=title,
                body="",
                parent_id=parent_id,
                type='page'
            )
            return result.get('id', '') if result else ''
        except Exception as error:
            logger.error(f"Error creating page: {error}")
            return ''

    def update_page_content(self, page_id: str, title: str, new_content: str) -> bool:
        """Updates the content of an existing page."""
        try:
            current_version = self.confluence.get_page_by_id(page_id, expand='version')['version']['number']
            self.confluence.update_page(
                page_id=page_id,
                title=title,
                body=new_content,
                type='page',
                representation='storage',
                minor_edit=False,
                version=current_version + 1
            )
            return True
        except Exception as error:
            logger.error(f"Error updating page {page_id}: {error}")
            return False

    def append_to_page(self, page_id: str, title: str, append_content: str) -> bool:
        """Appends content to an existing page."""
        try:
            current_page = self.confluence.get_page_by_id(page_id, expand='body.storage')
            current_content = current_page['body']['storage']['value']
            current_version = current_page['version']['number']
            new_content = current_content + append_content
            self.confluence.update_page(
                page_id=page_id,
                title=title,
                body=new_content,
                type='page',
                representation='storage',
                minor_edit=False,
                version=current_version + 1
            )
            return True
        except Exception as error:
            logger.error(f"Error appending to page {page_id}: {error}")
            return False

    def page_exists(self, page_id: str) -> bool:
        """Checks if a page exists by ID."""
        try:
            page = self.confluence.get_page_by_id(page_id)
            return page is not None
        except Exception:
            return False

    def get_page_id_by_title(self, space: str, title: str) -> str:
        """Finds page ID by title and space."""
        try:
            pages = self.confluence.get_page_id(space, title)
            return pages if pages else ''
        except Exception as error:
            logger.error(f"Error finding page: {error}")
            return ''

    def delete_page(self, page_id: str) -> bool:
        """Deletes a page by ID."""
        try:
            self.confluence.remove_page(page_id)
            return True
        except Exception as error:
            logger.error(f"Error deleting page {page_id}: {error}")
            return False