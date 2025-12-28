# service/confluence_table_service.py

import re
from dataclasses import dataclass
from typing import List, Dict, Optional
import pandas as pd

from bs4 import BeautifulSoup
from atlassian import Confluence

@dataclass(frozen=True)
class TableColumn:
    name: str
    index: int


@dataclass
class ParsedTable:
    headers: List[str]
    rows: List[List[str]]
    raw_html: str

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
        html = self._get_page_storage_content(page_id)
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

        html = self._get_page_storage_content(page_id)
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

        html = self._get_page_storage_content(page_id)
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

    def get_filtered_rows(
            self,
            page_id: str,
            namespace: str,
            namespace_column_index: int = 0,
            start_row: int = 1,
    ) -> List[List[str]]:
        """
        Вырезает строки из таблицы на странице, найденной по ID, в которых содержится $namespace и возвращает LIST строк
        Если строки в таблице по $namespace не были найдены, возвращает пустой массив
        """

        table = self.get_table_by_row_content(page_id, namespace.upper(), column_index=namespace_column_index)
        if not table:
            return []

        filtered = []
        for row in table.rows[start_row:]:
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