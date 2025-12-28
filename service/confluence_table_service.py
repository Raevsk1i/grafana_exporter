# service/confluence_table_service.py

import re
import pandas as pd

from dataclasses import dataclass
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from atlassian import Confluence
from utils.confluence_utils import *

@dataclass(frozen=True)
class TableColumn:
    name: str
    index: int


@dataclass
class ParsedTable:
    headers: List[str]
    rows: List[List[str]]
    raw_html: str = ""

    def to_list_of_dicts(self) -> List[Dict[str, str]]:
        return [dict(zip(self.headers, row)) for row in self.rows]

    def to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(self.rows, columns=self.headers)


class ConfluenceTableService:
    """
    Сервис для чтения и парсинга таблиц из страниц Confluence.
    Получает готовый confluence клиент через dependency injection.
    """

    def __init__(self, confluence_client: Confluence):
        self.confluence = confluence_client

    def _get_page_storage_content_by_id(self, page_id: str) -> str:
        """
        Получается всю информацию со страницы по ее ID и возвращает ее body
        """

        page = self.confluence.get_page_by_id(page_id, expand="body.storage")
        return page["body"]["storage"]["value"]

    def _parse_all_tables(self, html_content: str) -> List[ParsedTable]:
        """
        Парсит все таблицы на странице и возвращает всех их в LIST
        """

        soup = BeautifulSoup(html_content, "html.parser")
        parsed_tables = []

        for table in soup.find_all("table"):
            all_rows = table.find_all("tr")
            if not all_rows:
                continue  # пустая таблица — пропускаем

            # Попробуем взять заголовки из <th> в первой строке
            first_row = all_rows[0]
            headers = [th.get_text(strip=True) for th in first_row.find_all("th")]

            # Если <th> нет — берём первую строку как заголовки (из <td>)
            if not headers:
                headers = [td.get_text(strip=True) for td in first_row.find_all("td")]
                data_rows = all_rows[1:]  # данные начинаются со второй строки
            else:
                data_rows = all_rows[1:]  # данные со второй строки

            # Если и в <td> ничего нет — заголовков нет
            if not headers:
                headers = []

            # Парсим строки данных
            rows = []
            for row in data_rows:
                cells = row.find_all(["td", "th"])
                rows.append([cell.get_text(strip=True) for cell in cells])

            parsed_tables.append(
                ParsedTable(
                    headers=headers,
                    rows=rows,
                    raw_html=str(table),
                )
            )
        return parsed_tables

    def get_table_by_index(self, page_id: str, index: int = 0) -> Optional[ParsedTable]:
        """
        Получает таблицы со страницы по ее ID, саму таблицу ищет по ее индексу
        Если таблица не найдена, возвращает None
        """
        html = self._get_page_storage_content_by_id(page_id)
        tables = self._parse_all_tables(html)
        return tables[index] if index < len(tables) else None

    def get_table_by_header_text(
            self,
            page_id: str,
            header_text: str,
            case_sensitive: bool = False,
            partial_match: bool = True,
    ) -> Optional[ParsedTable]:
        """
        Получает таблицу со страницы по ID, таблица ищется по заголовкам (в основном в самой первой строке)
        Если таблица по заголовкам не найдена, возвращается None
        """

        html = self._get_page_storage_content_by_id(page_id)
        tables = self._parse_all_tables(html)

        flag = re.IGNORECASE if not case_sensitive else 0
        pattern = re.compile(re.escape(header_text), flag)

        for table in tables:
            if partial_match:
                if any(pattern.search(h) for h in table.headers):
                    return table
            else:
                if any(pattern.fullmatch(h) for h in table.headers):
                    return table
        return None

    def get_table_by_row_content(
            self,
            page_id: str,
            search_value: str,
            column_index: Optional[int] = None,
            case_sensitive: bool = False,
    ) -> Optional[ParsedTable]:
        """
        Получает таблицу со страницы по ID, таблица ищется по ключевым словам во всех строках таблицы по индексу столбца
        Если таблица по ключевым словам не найдена, возвращается None
        """

        if not search_value.strip():
            return None

        html = self._get_page_storage_content_by_id(page_id)
        tables = self._parse_all_tables(html)

        flag = re.IGNORECASE if not case_sensitive else 0
        pattern = re.compile(re.escape(search_value), flag)

        for table in tables:
            for row in table.rows:
                if column_index is not None:
                    if column_index < len(row) and pattern.search(row[column_index]):
                        return table
                else:
                    if any(pattern.search(cell) for cell in row):
                        return table
        return None

    def get_filtered_rows_with_first_column_namespace(
            self,
            page_id: str,
            namespace: str,
            namespace_column_index: int = 0,
            start_row: int = 0,  # Изменено с 1 на 0!
    ) -> List[List[str]]:
        """
        Вырезает строки из таблицы на странице, найденной по ID,
        в которых содержится $namespace и возвращает LIST строк без колонки namespace.
        Если строки не найдены — возвращает пустой список.
        """
        table = self.get_table_by_row_content(page_id, namespace.upper(), column_index=namespace_column_index)
        if not table:
            return []

        filtered = []
        for row in table.rows[start_row:]:  # start_row=0 по умолчанию — все данные
            if len(row) > namespace_column_index and namespace.upper() in row[namespace_column_index].upper():
                filtered.append(row[1:])  # пропускаем колонку с namespace
        return filtered

    def get_table_as_dataframe(
            self,
            page_id: str,
            index: Optional[int] = None,
            header_text: Optional[str] = None,
    ) -> Optional[pd.DataFrame]:
        """
        Этот метод извлекает одну таблицу по индексу со страницы, найденной по ID, и преобразует её в pandas DataFrame.
        Если таблица не найдена, возвращает None
        """

        if index is not None:
            table = self.get_table_by_index(page_id, index)
        elif header_text:
            table = self.get_table_by_header_text(page_id, header_text)
        else:
            table = self.get_table_by_index(page_id, 0)

        return table.to_dataframe() if table else None

    def convert_table_to_html(
            self,
            table: ParsedTable,
            include_styles: bool = True,
            table_class: str = "confluence-table",
    ) -> str:
        """
        Преобразует объект ParsedTable в валидный HTML-код таблицы,
        который можно напрямую вставить в HTML-документ.

        Аргументы:
            table: ParsedTable — распаршенная таблица
            include_styles: bool — добавлять ли встроенные CSS-стили для красивого отображения
            table_class: str — класс для <table>, полезно для последующей стилизации

        Возвращает:
            str — полный HTML-код таблицы
        """
        if not table.headers and not table.rows:
            return "<!-- Пустая таблица -->"

        html_parts = []

        if include_styles:
            html_parts.append(
                '<style>'
                'table.confluence-table { border-collapse: collapse; width: 100%; margin: 20px 0; font-family: Arial, sans-serif; }'
                'table.confluence-table th, table.confluence-table td { border: 1px solid #ddd; padding: 10px; text-align: left; }'
                'table.confluence-table th { background-color: #f4f5f7; font-weight: bold; }'
                'table.confluence-table tr:nth-child(even) { background-color: #f9f9f9; }'
                'table.confluence-table tr:hover { background-color: #f1f1f1; }'
                '</style>'
            )

        html_parts.append(f'<table class="{table_class}">')

        # Заголовок таблицы, если есть
        if table.headers:
            html_parts.append('<thead>')
            html_parts.append('<tr>')
            for header in table.headers:
                html_parts.append(f'<th>{escape_html(header)}</th>')
            html_parts.append('</tr>')
            html_parts.append('</thead>')

        # Тело таблицы
        html_parts.append('<tbody>')
        for row in table.rows:
            html_parts.append('<tr>')
            # Количество ячеек в строке может отличаться от количества заголовков
            for cell in row:
                html_parts.append(f'<td>{escape_html(cell)}</td>')
            # Если в строке меньше ячеек — дополняем пустыми <td>
            if table.headers and len(row) < len(table.headers):
                for _ in range(len(table.headers) - len(row)):
                    html_parts.append('<td></td>')
            html_parts.append('</tr>')
        html_parts.append('</tbody>')

        html_parts.append('</table>')

        return '\n'.join(html_parts)

