import logging
from pathlib import Path
from typing import List, Dict, Optional, Any, Callable, TypeVar, Union

import requests
from atlassian import Confluence
from atlassian.errors import (
    ApiError, ApiConflictError, ApiNotFoundError, ApiPermissionError
)

T = TypeVar("T")


def _validate_str(value: Optional[str], name: str) -> str:
    """Строковый аргумент не должен быть пустым."""
    if not value or not value.strip():
        raise ValueError(f"{name} must not be empty")
    return value.strip()


def safe_api_call(default=None) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Декоратор для безопасного вызова Confluence API.
    Логирует и возвращает default при ошибке.
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        def wrapper(*args, **kwargs) -> T:
            try:
                return func(*args, **kwargs)
            except ApiNotFoundError:
                logging.info(f"{func.__name__}: объект не найден")
                return default
            except ApiConflictError as e:
                logging.warning(f"{func.__name__}: конфликт данных — {e}")
                return default
            except ApiPermissionError as e:
                logging.error(f"{func.__name__}: недостаточно прав — {e}")
                return default
            except ApiError as e:
                logging.error(f"{func.__name__}: API ошибка — {e}")
                return default
            except requests.RequestException as e:
                logging.error(f"{func.__name__}: сетевая ошибка — {e}")
                return default
            except Exception:
                logging.exception(f"{func.__name__}: критическая ошибка")
                return default
        return wrapper
    return decorator


class ConfluencePageService:
    """Сервис управления страницами и вложениями в Confluence."""

    def __init__(self, confluence_client: Confluence):
        self.confluence = confluence_client

    # ========================
    # Работа со страницами
    # ========================

    @safe_api_call(default=None)
    def create_page(
            self, space: str, title: str, body: str = "",
            parent_id: Optional[str] = None
    ) -> Optional[str]:
        space = _validate_str(space, "space")
        title = _validate_str(title, "title")

        result = self.confluence.create_page(
            space=space,
            title=title,
            body=body,
            parent_id=parent_id,
            type="page",
            representation="storage",
        )
        return result.get("id")

    @safe_api_call(default=False)
    def page_exists(self, page_id: Optional[str]) -> bool:
        page_id = _validate_str(page_id, "page_id")
        page = self.confluence.get_page_by_id(page_id)
        return page is not None

    @safe_api_call(default=None)
    def get_page_id_by_title(self, space: str, title: str) -> Optional[str]:
        space = _validate_str(space, "space")
        title = _validate_str(title, "title")
        return self.confluence.get_page_id(space, title)

    @safe_api_call(default=False)
    def delete_page(self, page_id: Optional[str]) -> bool:
        page_id = _validate_str(page_id, "page_id")
        if not self.page_exists(page_id):
            logging.info(f"delete_page: {page_id} уже удалена")
            return True

        self.confluence.remove_page(page_id)
        logging.info(f"Страница {page_id} удалена")
        return True

    @safe_api_call(default=None)
    def get_page_content(self, page_id: Optional[str]) -> Optional[str]:
        page_id = _validate_str(page_id, "page_id")

        page = self.confluence.get_page_by_id(page_id, expand="body.storage")
        storage = page.get("body", {}).get("storage", {})
        return storage.get("value")  # может быть None или ""

    @safe_api_call(default=False)
    def update_page(
            self, page_id: Optional[str], title: str, new_body: str,
            minor_edit: bool = False
    ) -> bool:
        page_id = _validate_str(page_id, "page_id")
        title = _validate_str(title, "title")

        self.confluence.update_page(
            page_id=page_id,
            title=title,
            body=new_body,
            representation="storage",
            minor_edit=minor_edit,
        )
        logging.info(f"update_page: {page_id} обновлена")
        return True

    @safe_api_call(default=None)
    def append_to_page(
            self, page_id: Optional[str], title: str, append_body: str,
            minor_edit: bool = False
    ) -> bool:
        """Обертка через update_page, чтобы не дублировать append_page."""
        current = self.get_page_content(page_id)
        if current is None:
            logging.warning(f"append_to_page: нет такой страницы {page_id}")
            return False

        return self.update_page(page_id, title, current + append_body, minor_edit)

    @safe_api_call(default=None)
    def replace_content_in_page(
            self, page_id: str, title: str, new_content: str,
            placeholder: str = "TOCHANGEFROMPYTHONEXPORTER"
    ) -> bool:
        current_body = self.get_page_content(page_id)
        if not current_body or placeholder not in current_body:
            logging.warning(f"replace_content: плейсхолдер не найден в {page_id}")
            return False

        return self.update_page(
            page_id, title, current_body.replace(placeholder, new_content)
        )

    # ========================
    # Работа с вложениями
    # ========================

    @safe_api_call(default=False)
    def upload_attachment(
        self,
        page_id: str,
        file_path: Union[str, Path],
        comment: Optional[str] = None,
    ) -> bool:
        file_path = Path(file_path)
        if not file_path.exists():
            logging.error(f"Файл не найден: {file_path}")
            return False

        self.confluence.attach_file(
            filename=str(file_path),
            page_id=page_id,
            comment=comment or file_path.name,
        )
        logging.info(f"upload_attachment: {file_path.name} загружен → {page_id}")
        return True

    def upload_attachments(
        self, page_id: str, file_paths: List[Union[str, Path]],
        comment_prefix: Optional[str] = None,
    ) -> List[str]:
        uploaded = []
        for path in file_paths:
            comment = f"{comment_prefix} {Path(path).stem}" if comment_prefix else None
            if self.upload_attachment(page_id, path, comment):
                uploaded.append(str(path))
        return uploaded

    @safe_api_call(default=[])
    def get_attachments(self, page_id: str) -> List[Dict[str, Any]]:
        return self.confluence.get_attachments_from_content(page_id).get("results", [])

    def delete_all_attachments(self, page_id: str) -> int:
        removed = 0
        for att in self.get_attachments(page_id):
            if self.delete_attachment_by_filename(page_id, att["title"]):
                removed += 1
        return removed

    @safe_api_call(default=False)
    def delete_attachment_by_filename(self, page_id: str, filename: str) -> bool:
        self.confluence.delete_attachment(page_id, filename)
        logging.info(f"delete_attachment: {filename} удалён из {page_id}")
        return True
