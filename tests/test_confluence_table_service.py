import pytest
from unittest.mock import Mock, patch
from pathlib import Path
import pandas as pd

from service.confluence_table_service import ConfluenceTableService, ParsedTable
from utils.confluence_utils import escape_html


# -------------------------
# ФИКСТУРЫ
# -------------------------

@pytest.fixture
def mock_confluence():
    return Mock()


@pytest.fixture
def service(mock_confluence, test_html):
    svc = ConfluenceTableService(mock_confluence)
    # Мокаем внутренний метод получения контента страницы
    svc._get_page_storage_content_by_id = Mock(return_value=test_html)
    return svc


@pytest.fixture(scope="session")
def test_html():
    path = Path("./props/test_html.html")
    return path.read_text(encoding="utf-8")


# -------------------------
# ТЕСТЫ ПАРСИНГА ТАБЛИЦ
# -------------------------

def test__parse_all_tables_basic(service, test_html):
    tables = service._parse_all_tables(test_html)

    # Всего было 6 таблиц, одна пустая → остаётся 5
    assert len(tables) == 5

    # Таблица 0
    assert tables[0].headers == ["Name", "Role", "Email", "Experience (years)"]
    assert tables[0].rows[0] == ["John Doe", "Developer", "john@example.com", "5"]

    # Таблица 1
    assert tables[1].headers == ["Category", "Allocated ($)", "Spent ($)", "Remaining ($)"]
    assert tables[1].rows[-1] == ["Misc", "1000", "200", "800"]

    # Таблица 2
    assert tables[2].rows[4] == ["global", "init", "Initialization function", "none"]

    # Таблица 3
    assert tables[3].rows[0] == ["001", "admin", "Administrator", "Fullaccess"]

    # Таблица 4
    assert tables[4].headers == ["Category", "Subcategory", "Value"]
    assert tables[4].rows[1] == ["Banana", "Yellow"]


# -------------------------
# get_table_by_index
# -------------------------

def test_get_table_by_index(service):
    assert service.get_table_by_index("id", 0) is not None
    assert service.get_table_by_index("id", 4).headers[0] == "Category"
    assert service.get_table_by_index("id", 5) is None

    # индекс -1 возвращает последнюю таблицу (поведение Python)
    assert service.get_table_by_index("id", -1) == service.get_table_by_index("id", 4)

    # по умолчанию index=0
    assert service.get_table_by_index("id").headers[0] == "Name"


# -------------------------
# get_table_by_header_text
# -------------------------

def test_get_table_by_header_text_exact_match(service):
    table = service.get_table_by_header_text("id", "Remaining ($)", partial_match=False)
    assert table is not None
    assert table.headers[-1] == "Remaining ($)"

    # регистронезависимость
    assert service.get_table_by_header_text("id", "namespace", partial_match=False)

    # регистрозависимый — не должен найти
    assert service.get_table_by_header_text("id", "namespace", partial_match=False, case_sensitive=True) is None

    # нет точного совпадения
    assert service.get_table_by_header_text("id", "Names", partial_match=False) is None


def test_get_table_by_header_text_partial_match(service):
    assert service.get_table_by_header_text("id", "User") is not None
    assert service.get_table_by_header_text("id", "experience") is not None
    assert service.get_table_by_header_text("id", "Product") is None


# -------------------------
# get_table_by_row_content
# -------------------------

@pytest.mark.parametrize("search,expected_column", [
    ("std", "Namespace"),
    ("cout", "Function Name"),
    ("admin", "Username"),
])
def test_get_table_by_row_content_any_column(service, search, expected_column):
    table = service.get_table_by_row_content("id", search)
    assert table is not None
    assert expected_column in table.headers


def test_get_table_by_row_content_column_index(service):
    table = service.get_table_by_row_content("id", "cout", column_index=1)
    assert table is not None

    assert service.get_table_by_row_content("id", "nonexistent", column_index=0) is None


# -------------------------
# get_filtered_rows_with_first_column_namespace
# -------------------------

def test_get_filtered_rows_with_first_column_namespace(service):
    rows = service.get_filtered_rows_with_first_column_namespace("id", "std")
    assert len(rows) == 3

    expected = {
        ("cout", "Standard output stream", "value"),
        ("printf", "Formatted print", "format, args"),
        ("vector", "Dynamic array", "size"),
    }
    assert {tuple(r) for r in rows} == expected


# -------------------------
# get_table_as_dataframe
# -------------------------

def test_get_table_as_dataframe_by_index(service):
    df = service.get_table_as_dataframe("id", index=0)
    assert isinstance(df, pd.DataFrame)
    assert df.columns.tolist() == ["Name", "Role", "Email", "Experience (years)"]
    assert df.iloc[0].tolist() == ["John Doe", "Developer", "john@example.com", "5"]


def test_get_table_as_dataframe_by_header_text(service):
    df = service.get_table_as_dataframe("id", header_text="User")
    assert isinstance(df, pd.DataFrame)
    assert "User ID" in df.columns


def test_get_table_as_dataframe_not_found(service):
    with patch.object(service, "get_table_by_index", return_value=None):
        assert service.get_table_as_dataframe("id", index=999) is None


# -------------------------
# convert_table_to_html
# -------------------------

def test_convert_table_to_html_basic(service):
    table = ParsedTable(
        headers=["Имя", "Возраст"],
        rows=[["Анна", "25"]],
    )
    html = service.convert_table_to_html(table)
    assert '<table class="confluence-table">' in html
    assert "<th>Имя</th>" in html
    assert "<td>Анна</td>" in html


def test_convert_table_to_html_no_styles(service):
    table = ParsedTable(headers=["A"], rows=[["1"]])
    html = service.convert_table_to_html(table, include_styles=False)
    assert "<style>" not in html


def test_convert_table_to_html_empty(service):
    html = service.convert_table_to_html(ParsedTable(headers=[], rows=[]))
    assert html.strip() == "<!-- Пустая таблица -->"


def test_convert_table_to_html_uneven_rows(service):
    table = ParsedTable(
        headers=["A", "B", "C"],
        rows=[["x", "y"]],
    )
    html = service.convert_table_to_html(table)
    assert "<td></td>" in html  # заполняется недостающая ячейка


# -------------------------
# escape_html
# -------------------------

def test_escape_html():
    dangerous = '"><script>alert("XSS")</script>'
    expected = '&quot;&gt;&lt;script&gt;alert(&quot;XSS&quot;)&lt;/script&gt;'
    assert escape_html(dangerous) == expected
