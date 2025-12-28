import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from service.confluence_page_service import ConfluencePageService


@pytest.fixture
def mock_confluence():
    """Создаёт мок клиента Confluence."""
    return MagicMock()


@pytest.fixture
def service(mock_confluence):
    """Возвращает сервис с замоканным confluence клиентом."""
    return ConfluencePageService(mock_confluence)


# ========================
# Работа со страницами
# ========================

def test_create_page_success(service, mock_confluence):
    mock_confluence.create_page.return_value = {"id": "123"}
    result = service.create_page("SPACE", "My title", "Body content")
    assert result == "123"
    mock_confluence.create_page.assert_called_once()


def test_create_page_empty_title(service):
    assert service.create_page("SPACE", "", "body") is None


def test_page_exists_true(service, mock_confluence):
    mock_confluence.get_page_by_id.return_value = {"id": "123"}
    assert service.page_exists("123") is True


def test_page_exists_false(service, mock_confluence):
    mock_confluence.get_page_by_id.return_value = None
    assert service.page_exists("123") is False


def test_get_page_id_by_title_found(service, mock_confluence):
    mock_confluence.get_page_id.return_value = "456"
    assert service.get_page_id_by_title("SPACE", "Title") == "456"


def test_delete_page_exists(service, mock_confluence):
    mock_confluence.get_page_by_id.return_value = {"id": "123"}
    assert service.delete_page("123") is True
    mock_confluence.remove_page.assert_called_once_with("123")


def test_delete_page_not_exists(service, mock_confluence, caplog):
    mock_confluence.get_page_by_id.return_value = None
    assert service.delete_page("123") is True   # идемпотентно: нет страницы — ок
    mock_confluence.remove_page.assert_not_called()


def test_get_page_content_value(service, mock_confluence):
    mock_confluence.get_page_by_id.return_value = {
        "body": {"storage": {"value": "<p>test</p>"}}
    }
    assert service.get_page_content("111") == "<p>test</p>"


def test_get_page_content_missing(service, mock_confluence):
    mock_confluence.get_page_by_id.return_value = {}
    assert service.get_page_content("111") is None


def test_update_page_success(service, mock_confluence):
    assert service.update_page("111", "Title", "<p>new</p>") is True
    mock_confluence.update_page.assert_called_once()


def test_append_to_page_success(service, mock_confluence):
    mock_confluence.get_page_by_id.return_value = {
        "body": {"storage": {"value": "<p>curr</p>"}}
    }

    assert service.append_to_page("1", "Title", "<p>new</p>") is True
    mock_confluence.update_page.assert_called_once()
    args, kwargs = mock_confluence.update_page.call_args
    assert "<p>curr</p><p>new</p>" in kwargs["body"]


def test_append_to_page_no_page(service, mock_confluence):
    mock_confluence.get_page_by_id.return_value = None
    assert service.append_to_page("1", "Title", "X") is False


def test_replace_content_success(service, mock_confluence):
    mock_confluence.get_page_by_id.return_value = {
        "body": {"storage": {"value": "AAA PLACE BBB"}}
    }

    assert service.replace_content_in_page("1", "Title", "XXX", "PLACE")
    mock_confluence.update_page.assert_called_once()


def test_replace_content_placeholder_not_found(service, mock_confluence):
    mock_confluence.get_page_by_id.return_value = {
        "body": {"storage": {"value": "no placeholder"}}
    }
    assert service.replace_content_in_page("1", "Title", "xxx") is False


# ========================
# Работа с вложениями
# ========================

def test_upload_attachment_success(service, mock_confluence, tmp_path):
    test_file = tmp_path / "file.txt"
    test_file.write_text("data")

    assert service.upload_attachment("1", test_file) is True
    mock_confluence.attach_file.assert_called_once()


def test_upload_attachment_no_file(service):
    assert service.upload_attachment("1", "no_such_file.txt") is False


def test_upload_attachments_multiple(service, mock_confluence, tmp_path):
    f1 = tmp_path / "a.txt"; f1.write_text("1")
    f2 = tmp_path / "b.txt"; f2.write_text("2")

    uploaded = service.upload_attachments("1", [f1, f2], comment_prefix="Charts")
    assert uploaded == [str(f1), str(f2)]
    assert mock_confluence.attach_file.call_count == 2


def test_get_attachments(service, mock_confluence):
    mock_confluence.get_attachments_from_content.return_value = {
        "results": [{"id": "1"}, {"id": "2"}]
    }
    res = service.get_attachments("1")
    assert len(res) == 2


def test_delete_attachment_by_filename_success(service, mock_confluence):
    assert service.delete_attachment_by_filename("1", "file.txt") is True
    mock_confluence.delete_attachment.assert_called_once_with("1", "file.txt")


def test_delete_all_attachments(service, mock_confluence):
    mock_confluence.get_attachments_from_content.return_value = {
        "results": [{"title": "f1"}, {"title": "f2"}]
    }
    mock_confluence.delete_attachment.return_value = True

    deleted = service.delete_all_attachments("1")
    assert deleted == 2
    assert mock_confluence.delete_attachment.call_count == 2
