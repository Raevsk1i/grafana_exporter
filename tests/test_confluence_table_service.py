# tests/test_confluence_table_service.py

import unittest
from unittest.mock import Mock, patch
import pandas as pd

from service.confluence_table_service import ConfluenceTableService, ParsedTable
from utils.confluence_utils import escape_html

# Путь к тестовому HTML относительно расположения тестового файла
TEST_HTML_PATH = "./props/test_html.html"

# Читаем содержимое файла один раз при загрузке модуля
with open(TEST_HTML_PATH, "r", encoding="utf-8") as f:
    TEST_HTML = f.read()


class TestConfluenceTableService(unittest.TestCase):

    def setUp(self):
        self.mock_confluence = Mock()
        self.service = ConfluenceTableService(self.mock_confluence)

        # Подменяем получение контента страницы на наш тестовый HTML
        self.service._get_page_storage_content_by_id = Mock(return_value=TEST_HTML)

    def test__parse_all_tables_basic(self):
        """
        Тестовый план для _parse_all_tables:
        - Проверяем общее количество распаршенных таблиц (ожидаем 5, т.к. Полностью пустая таблица №4 пропускается по логике парсера).
        - Проверяем структуру каждой таблицы:
          - Заголовки (headers): должны извлекаться из <th> или первой строки <td>.
          - Строки данных (rows): все последующие строки, текст очищен (strip=True), включая вложенные элементы как <b> или <a> (текст извлекается без тегов).
          - Проверяем конкретные значения в заголовках и строках для каждой таблицы.
          - Для таблицы с rowspan: парсер не обрабатывает объединения, так что ожидаем простое извлечение ячеек по строкам (rowspan не распаковывается, но текст извлекается как есть).
        - Граничные случаи: пустая таблица пропущена, таблицы с разными классами и стилями парсятся корректно.
        - Обеспечиваем, что raw_html сохраняется для каждой таблицы (но не проверяем его содержимое в этом базовом тесте).
        """
        tables = self.service._parse_all_tables(TEST_HTML)

        # Общее количество: 6 таблиц в HTML, но пустая №4 пропущена → 5 таблиц
        self.assertEqual(len(tables), 5)

        # Таблица 0: Team Members (TH headers)
        self.assertEqual(tables[0].headers, ["Name", "Role", "Email", "Experience (years)"])
        self.assertEqual(len(tables[0].rows), 3)
        self.assertEqual(tables[0].rows[0], ["John Doe", "Developer", "john@example.com", "5"])
        self.assertEqual(tables[0].rows[1], ["Jane Smith", "Designer", "jane@example.com", "8"])
        self.assertEqual(tables[0].rows[2], ["Bob Johnson", "Manager", "bob@example.com", "10"])

        # Таблица 1: Budget Breakdown (headers from TD)
        self.assertEqual(tables[1].headers, ["Category", "Allocated ($)", "Spent ($)", "Remaining ($)"])
        self.assertEqual(len(tables[1].rows), 4)
        self.assertEqual(tables[1].rows[0], ["Hardware", "5000", "3000", "2000"])
        self.assertEqual(tables[1].rows[3], ["Misc", "1000", "200", "800"])

        # Таблица 2: Namespace and Functions
        self.assertEqual(tables[2].headers, ["Namespace", "Function Name", "Description", "Parameters"])
        self.assertEqual(len(tables[2].rows), 5)
        self.assertEqual(tables[2].rows[0], ["std", "cout", "Standard output stream", "value"])
        self.assertEqual(tables[2].rows[4], ["global", "init", "Initialization function", "none"])

        # Таблица 3: User Permissions (бывшая №5, с вложенными тегами — текст очищен)
        self.assertEqual(tables[3].headers, ["User ID", "Username", "Role", "Access Level"])
        self.assertEqual(len(tables[3].rows), 3)
        self.assertEqual(tables[3].rows[0], ["001", "admin", "Administrator", "Fullaccess"])  # <b> и <a> текст извлечён
        self.assertEqual(tables[3].rows[2], ["003", "editor", "Editor", "Edit pages"])

        # Таблица 4: Additional Table with Rowspan (бывшая №6, парсер извлекает как есть, без распаковки rowspan)
        self.assertEqual(tables[4].headers, ["Category", "Subcategory", "Value"])
        self.assertEqual(len(tables[4].rows), 3)
        self.assertEqual(tables[4].rows[0], ["Fruits", "Apple", "Red"])  # rowspan не влияет на список, первая строка полная
        self.assertEqual(tables[4].rows[1], ["Banana", "Yellow"])  # вторая строка без первой ячейки (из-за rowspan, но парсер берёт только существующие cells)
        self.assertEqual(tables[4].rows[2], ["Vegetables", "Carrot", "Orange"])

    def test_get_table_by_index(self):
        """
        Тест для get_table_by_index(page_id, index).
        В TEST_HTML: 6 таблиц, но одна полностью пустая (Table 4) → должна быть пропущена.
        Ожидаем ровно 5 таблиц в результате.
        Валидные индексы: 0–4
        """

        # Сначала проверяем общее количество распаршенных таблиц
        html = self.service._get_page_storage_content_by_id("any")
        tables = self.service._parse_all_tables(html)
        self.assertEqual(len(tables), 5, "Пустая таблица должна быть пропущена!")

        # Индекс 0 — Team Members
        table = self.service.get_table_by_index("any_page_id", 0)
        self.assertIsNotNone(table)
        self.assertEqual(table.headers[0], "Name")

        # Индекс 1 — Budget Breakdown
        table = self.service.get_table_by_index("any_page_id", 1)
        self.assertIsNotNone(table)
        self.assertIn("Category", table.headers)

        # Индекс 2 — Namespace
        table = self.service.get_table_by_index("any_page_id", 2)
        self.assertIsNotNone(table)
        self.assertEqual(table.headers[0], "Namespace")

        # Индекс 3 — User Permissions
        table = self.service.get_table_by_index("any_page_id", 3)
        self.assertIsNotNone(table)
        self.assertIn("admin", table.rows[0])

        # Индекс 4 — Table with Rowspan (последняя)
        table = self.service.get_table_by_index("any_page_id", 4)
        self.assertIsNotNone(table)
        self.assertEqual(table.headers, ["Category", "Subcategory", "Value"])
        self.assertEqual(table.rows[1], ["Banana", "Yellow"])

        # Граничные случаи: за пределами
        table = self.service.get_table_by_index("any_page_id", 5)
        self.assertIsNone(table, "Индекс 5 должен возвращать None — всего 5 таблиц")

        table = self.service.get_table_by_index("any_page_id", 10)
        self.assertIsNone(table)

        table = self.service.get_table_by_index("any_page_id", -1) # ожидаем самую последнюю таблицу
        self.assertEqual(table, self.service.get_table_by_index("any_page_id", 4))

        # По умолчанию — первая таблица
        table = self.service.get_table_by_index("any_page_id")
        self.assertIsNotNone(table)
        self.assertEqual(table.headers[1], "Role")  # вторая колонка Team Members

    def test_get_table_by_header_text_exact_match(self):
        """
        Тест для метода get_table_by_header_text с точным совпадением (partial_match=False).
        Проверяем:
        - Поиск по полному точному тексту заголовка одной из колонок.
        - Регистронезависимость по умолчанию (case_sensitive=False).
        - Явное отключение частичного совпадения.
        - Возврат первой найденной таблицы, если несколько подходят.
        - Возврат None при отсутствии точного совпадения.
        - Корректную работу с заголовками, содержащими пробелы и спецсимволы (например, скобки).
        """

        page_id = "dummy_page_id"

        # 1. Точное совпадение: полное имя колонки
        table = self.service.get_table_by_header_text(page_id, "Name", partial_match=False)
        self.assertIsNotNone(table)
        self.assertEqual(table.headers[0], "Name")  # Team Members таблица
        self.assertIn("John Doe", table.rows[0])

        # 2. Точное совпадение: другая колонка из той же таблицы
        table = self.service.get_table_by_header_text(page_id, "Experience (years)", partial_match=False)
        self.assertIsNotNone(table)
        self.assertIn("Experience (years)", table.headers)

        # 3. Точное совпадение: колонка из Budget таблицы
        table = self.service.get_table_by_header_text(page_id, "Remaining ($)", partial_match=False)
        self.assertIsNotNone(table)
        self.assertEqual(table.headers[3], "Remaining ($)")
        self.assertIn(["Misc", "1000", "200", "800"], table.rows)

        # 4. Точное совпадение: колонка из Namespace таблицы
        table = self.service.get_table_by_header_text(page_id, "Function Name", partial_match=False)
        self.assertIsNotNone(table)
        self.assertEqual(table.headers[1], "Function Name")
        self.assertIn("cout", [row[1] for row in table.rows])

        # 5. Точное совпадение: колонка из User Permissions
        table = self.service.get_table_by_header_text(page_id, "Access Level", partial_match=False)
        self.assertIsNotNone(table)
        self.assertIn("Fullaccess", table.rows[0])

        # 6. Регистронезависимость (по умолчанию case_sensitive=False)
        table = self.service.get_table_by_header_text(page_id, "namespace", partial_match=False)
        self.assertIsNotNone(table)
        self.assertEqual(table.headers[0], "Namespace")

        # 7. С case_sensitive=True — не должно найти
        table = self.service.get_table_by_header_text(
            page_id, "namespace", partial_match=False, case_sensitive=True
        )
        self.assertIsNone(table)

        # 8. Нет точного совпадения — возвращает None
        table = self.service.get_table_by_header_text(page_id, "Names", partial_match=False)  # не "Name"
        self.assertIsNone(table)

        table = self.service.get_table_by_header_text(page_id, "Category ", partial_match=False)  # лишний пробел
        self.assertIsNone(table)

        table = self.service.get_table_by_header_text(page_id, "SubcategoryX", partial_match=False)
        self.assertIsNone(table)

        # 9. Частичное совпадение отключено — не должно найти подстроку
        table = self.service.get_table_by_header_text(page_id, "Level", partial_match=False)
        self.assertIsNone(table)  # "Access Level" ≠ "Level"

        table = self.service.get_table_by_header_text(page_id, "User", partial_match=False)
        self.assertIsNone(table)  # "User ID" ≠ "User"

        # 10. Проверка, что возвращается первая найденная таблица (если несколько имеют одинаковый заголовок)
        # В нашем HTML заголовков дубликатов нет, но логика должна работать корректно
        table = self.service.get_table_by_header_text(page_id, "Level")  # по умолчанию partial_match=True
        self.assertIsNotNone(table)  # найдёт "Access Level"

    def test_get_table_by_header_text_partial_match(self):
        table = self.service.get_table_by_header_text("123", "User")
        self.assertIsNotNone(table)
        self.assertIn("User ID", table.headers[0])

        table = self.service.get_table_by_header_text("123", "user", case_sensitive=False)
        self.assertIsNotNone(table)

        table = self.service.get_table_by_header_text("123", "user", case_sensitive=True)
        self.assertIsNone(table)  # "User" ≠ "user"

    def test_get_table_by_header_text_case_insensitive(self):
        table = self.service.get_table_by_header_text("123", "name", case_sensitive=False)
        self.assertIsNotNone(table)

    def test_get_table_by_row_content_by_column(self):
        table = self.service.get_table_by_row_content("123", "std", column_index=0)
        self.assertIsNotNone(table)
        self.assertEqual(table.headers[0], "Namespace")

        table = self.service.get_table_by_row_content("123", "cout", column_index=1)
        self.assertIsNotNone(table)

        table = self.service.get_table_by_row_content("123", "nonexistent", column_index=0)
        self.assertIsNone(table)

    def test_get_table_by_row_content_any_column(self):
        """
        Тест для get_table_by_row_content без указания column_index (поиск по любой колонке).
        Проверяем поиск по подстроке в любой ячейке любой строки таблицы.
        """

        page_id = "dummy"

        # 1. Поиск по подстроке в имени функции
        table = self.service.get_table_by_row_content(page_id, "log")
        self.assertIsNotNone(table)
        self.assertEqual(table.headers[1], "Function Name")  # Namespace таблица
        self.assertIn("log_error", [cell for row in table.rows for cell in row])

        # 2. Поиск по подстроке в описании
        table = self.service.get_table_by_row_content(page_id, "error")
        self.assertIsNotNone(table)
        self.assertIn("Logs an error message", [cell for row in table.rows for cell in row])

        # 3. Поиск по namespace
        table = self.service.get_table_by_row_content(page_id, "std")
        self.assertIsNotNone(table)
        self.assertIn("cout", [row[1] for row in table.rows])

        # 4. Поиск по параметру
        table = self.service.get_table_by_row_content(page_id, "message")
        self.assertIsNotNone(table)

        # 5. Регистронезависимость
        table = self.service.get_table_by_row_content(page_id, "STD")
        self.assertIsNotNone(table)

        table = self.service.get_table_by_row_content(page_id, "Std", case_sensitive=True)
        self.assertIsNone(table)  # с учётом регистра — не найдёт "std" или "STD::io"

        # 6. Поиск в другой таблице — User Permissions
        table = self.service.get_table_by_row_content(page_id, "admin")
        self.assertIsNotNone(table)
        self.assertIn("admin", table.rows[0])

        # 7. Нет совпадения
        table = self.service.get_table_by_row_content(page_id, "nonexistent123")
        self.assertIsNone(table)

        # 8. Пустой поиск — не должен найти
        table = self.service.get_table_by_row_content(page_id, "")
        self.assertIsNone(table)

    def test_get_filtered_rows(self):
        """
        Тест для get_filtered_rows.
        Метод ищет таблицу по подстроке в колонке namespace (по умолчанию 0),
        затем возвращает строки данных (начиная с start_row, по умолчанию 1),
        где эта колонка содержит namespace (регистронезависимо через 'in'),
        и удаляет колонку namespace (row[1:]).
        """

        page_id = "123"

        # Основной кейс: "std" — должно найти 3 строки (cout, printf, vector)
        rows = self.service.get_filtered_rows_with_first_column_namespace(page_id, "std")

        self.assertEqual(3, len(rows))

        # Проверяем в правильном порядке появления в таблице
        self.assertEqual(rows[0], ["cout", "Standard output stream", "value"])
        self.assertEqual(rows[1], ["printf", "Formatted print", "format, args"])
        self.assertEqual(rows[2], ["vector", "Dynamic array", "size"])

        # Дополнительно: проверка через множество (более устойчиво к изменениям порядка)
        expected_rows = {
            ("cout", "Standard output stream", "value"),
            ("printf", "Formatted print", "format, args"),
            ("vector", "Dynamic array", "size"),
        }
        actual_rows = {tuple(row) for row in rows}
        self.assertEqual(actual_rows, expected_rows)

        # my::utils — точное совпадение
        rows = self.service.get_filtered_rows_with_first_column_namespace(page_id, "my::utils")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0], ["log_error", "Logs an error message", "message"])

        # global
        rows = self.service.get_filtered_rows_with_first_column_namespace(page_id, "global")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0], ["init", "Initialization function", "none"])

        # Несуществующий namespace
        rows = self.service.get_filtered_rows_with_first_column_namespace(page_id, "nonexistent")
        self.assertEqual(len(rows), 0)

        # Регистронезависимость
        rows = self.service.get_filtered_rows_with_first_column_namespace(page_id, "STD")
        self.assertEqual(len(rows), 3)

        # start_row=0 — не должен включать заголовок (он не содержит "std")
        rows = self.service.get_filtered_rows_with_first_column_namespace(page_id, "std", start_row=0)
        self.assertEqual(len(rows), 3)

    def test_get_filtered_rows_start_row(self):
        rows = self.service.get_filtered_rows_with_first_column_namespace("123", "std", start_row=0)
        # start_row=0 включает первую строку данных (без заголовка)
        self.assertEqual(len(rows), 3)  # всё равно 3, потому что заголовок не содержит "std" в данных

    def test_get_table_as_dataframe_by_index(self):
        """
        Тест для get_table_as_dataframe с выбором таблицы по index.
        Проверяем преобразование ParsedTable в pandas.DataFrame.
        """

        page_id = "123"

        # Таблица по индексу 0 — Team Members
        df = self.service.get_table_as_dataframe(page_id, index=0)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(list(df.columns), ["Name", "Role", "Email", "Experience (years)"])
        self.assertEqual(len(df), 3)
        self.assertEqual(df.iloc[0].to_list(), ["John Doe", "Developer", "john@example.com", "5"])

        # Таблица по индексу 1 — Budget Breakdown (заголовки из первой строки TD)
        df = self.service.get_table_as_dataframe(page_id, index=1)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(list(df.columns), ["Category", "Allocated ($)", "Spent ($)", "Remaining ($)"])
        self.assertEqual(len(df), 4)
        self.assertIn("Hardware", df["Category"].tolist())

        # Таблица по индексу 2 — Namespace and Functions
        df = self.service.get_table_as_dataframe(page_id, index=2)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(list(df.columns)[0], "Namespace")
        self.assertEqual(len(df), 5)
        self.assertIn("cout", df["Function Name"].tolist())

        # Таблица по индексу 3 — User Permissions
        df = self.service.get_table_as_dataframe(page_id, index=3)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(list(df.columns), ["User ID", "Username", "Role", "Access Level"])
        self.assertEqual(len(df), 3)
        self.assertEqual(df.iloc[0]["Username"], "admin")  # текст из <b> извлечён корректно

        # Таблица по индексу 4 — Table with Rowspan
        df = self.service.get_table_as_dataframe(page_id, index=4)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(list(df.columns), ["Category", "Subcategory", "Value"])
        self.assertEqual(len(df), 3)

        # Первая строка — полная
        self.assertEqual(df.iloc[0].to_list(), ["Fruits", "Apple", "Red"])

        # Вторая строка — короткая: Category получает значение из первой ячейки ("Banana")
        # NaN в последней колонке (Value)
        self.assertEqual(df.iloc[1].to_list()[:2], ["Banana", "Yellow"])
        self.assertTrue(pd.isna(df.iloc[1]["Value"]))

        # Третья строка — полная
        self.assertEqual(df.iloc[2].to_list(), ["Vegetables", "Carrot", "Orange"])

        # Category в строке 1 не NaN (потому что pandas заполняет справа)
        self.assertFalse(pd.isna(df.iloc[1]["Category"]))
        self.assertEqual(df.iloc[1]["Category"], "Banana")

    def test_get_table_as_dataframe_by_header_text(self):
        """
        Тест для get_table_as_dataframe с выбором таблицы по header_text.
        По умолчанию используется частичное совпадение (partial_match=True).
        Для тестирования точного совпадения используем напрямую get_table_by_header_text.
        """

        page_id = "123"

        # 1. Частичное совпадение (по умолчанию): "User" → находит User Permissions
        df = self.service.get_table_as_dataframe(page_id, header_text="User")
        self.assertIsInstance(df, pd.DataFrame)
        self.assertIn("User ID", df.columns)
        self.assertEqual(len(df), 3)
        self.assertEqual(df.iloc[0]["Username"], "admin")

        # 2. Частичное совпадение: "experience" (регистронезависимо)
        df = self.service.get_table_as_dataframe(page_id, header_text="experience")
        self.assertIsInstance(df, pd.DataFrame)
        self.assertIn("Experience (years)", df.columns)

        # 3. Частичное совпадение: "Category" → Budget Breakdown
        df = self.service.get_table_as_dataframe(page_id, header_text="Category")
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(df.columns[0], "Category")

        # 4. Не найдено → None
        df = self.service.get_table_as_dataframe(page_id, header_text="Product")
        self.assertIsNone(df)

        # 5. Тестируем точное совпадение через get_table_by_header_text
        # Точный заголовок "User ID" — найдёт таблицу
        table = self.service.get_table_by_header_text(page_id, "User ID", partial_match=False)
        self.assertIsNotNone(table)
        df_exact = table.to_dataframe()
        self.assertIsInstance(df_exact, pd.DataFrame)
        self.assertEqual(df_exact.columns[0], "User ID")

        # Точного заголовка "User" нет — не найдёт
        table = self.service.get_table_by_header_text(page_id, "User", partial_match=False)
        self.assertIsNone(table)
        df_exact = table.to_dataframe() if table else None
        self.assertIsNone(df_exact)  # Здесь проверяем None, а не DataFrame!

    def test_get_table_as_dataframe_default_first_table(self):
        df = self.service.get_table_as_dataframe("123")
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(list(df.columns), ["Name", "Role", "Email", "Experience (years)"])

    def test_get_table_as_dataframe_not_found(self):
        with patch.object(self.service, 'get_table_by_index', return_value=None):
            df = self.service.get_table_as_dataframe("123", index=999)
            self.assertIsNone(df)

    def test__escape_html(self):
        """Тестируем экранирование опасных символов"""
        dangerous_text = '"><script>alert("XSS")</script><br>'
        expected = '&quot;&gt;&lt;script&gt;alert(&quot;XSS&quot;)&lt;/script&gt;&lt;br&gt;'
        result = escape_html(dangerous_text)
        self.assertEqual(result, expected)

        # Обычный текст без изменений
        safe_text = "Обычный текст & данные"
        expected_safe = "Обычный текст &amp; данные"
        self.assertEqual(escape_html(safe_text), expected_safe)

    def test_parsed_table_to_html_basic(self):
        """Базовая таблица с заголовками и данными"""
        table = ParsedTable(
            headers=["Имя", "Возраст", "Город"],
            rows=[
                ["Анна", "25", "Москва"],
                ["Борис", "30", "СПб"],
            ],
            raw_html="<table>...</table>"
        )

        html = self.service.convert_table_to_html(table)

        self.assertIn('<table class="confluence-table">', html)
        self.assertIn('<style>', html)  # стили включены по умолчанию
        self.assertIn('<thead>', html)
        self.assertIn('<th>Имя</th>', html)
        self.assertIn('<th>Возраст</th>', html)
        self.assertIn('<th>Город</th>', html)
        self.assertIn('<td>Анна</td>', html)
        self.assertIn('<td>30</td>', html)
        self.assertIn('<td>СПб</td>', html)
        self.assertIn('</table>', html)

    def test_parsed_table_to_html_without_styles(self):
        """Отключение встроенных стилей"""
        table = ParsedTable(
            headers=["A", "B"],
            rows=[["1", "2"]]
        )

        html = self.service.convert_table_to_html(table, include_styles=False)

        self.assertNotIn('<style>', html)
        self.assertIn('<table class="confluence-table">', html)
        self.assertIn('<th>A</th>', html)
        self.assertIn('<td>1</td>', html)

    def test_parsed_table_to_html_custom_class(self):
        """Пользовательский класс таблицы"""
        table = ParsedTable(headers=["Col"], rows=[["Data"]])

        html = self.service.convert_table_to_html(table, table_class="my-custom-table")

        self.assertIn('<table class="my-custom-table">', html)

    def test_parsed_table_to_html_uneven_rows(self):
        """Строки с разным количеством ячеек — должны дополняться пустыми <td>"""
        table = ParsedTable(
            headers=["Col1", "Col2", "Col3"],
            rows=[
                ["A", "B", "C"],
                ["X", "Y"],  # только 2 ячейки
                ["Only one"],  # только 1 ячейка
            ],
            raw_html=""
        )

        html = self.service.convert_table_to_html(table)

        # Проверяем, что в строках с недостающими ячейками есть пустые <td>
        self.assertIn('<tr><td>A</td><td>B</td><td>C</td></tr>', html.replace('\n', ''))
        self.assertIn('<tr><td>X</td><td>Y</td><td></td></tr>', html.replace('\n', ''))
        self.assertIn('<tr><td>Only one</td><td></td><td></td></tr>', html.replace('\n', ''))

    def test_convert_table_to_html_no_headers(self):
        """Таблица без заголовков — только <td>"""
        table = ParsedTable(
            headers=[],
            rows=[
                ["Данные1", "Данные2"],
                ["Еще", "Строка"],
            ],
            raw_html=""
        )

        html = self.service.convert_table_to_html(table)

        self.assertNotIn('<thead>', html)
        self.assertNotIn('<th>', html)
        self.assertIn('<td>Данные1</td>', html)
        self.assertIn('<td>Еще</td>', html)

    def test_convert_table_to_html_empty_table(self):
        """Пустая таблица — должен вернуться комментарий"""
        empty_table = ParsedTable(headers=[], rows=[], raw_html="")

        html = self.service.convert_table_to_html(empty_table)

        self.assertEqual(html.strip(), "<!-- Пустая таблица -->")

    def test_convert_table_to_html_with_special_chars(self):
        """Содержимое ячеек с HTML-символами должно быть экранировано"""
        table = ParsedTable(
            headers=["<script>", "& > \" '"],
            rows=[
                ['"><img src=x onerror=alert(1)>', "Тест & тест"]
            ]
        )

        html = self.service.convert_table_to_html(table)

        self.assertIn('&lt;script&gt;', html)
        self.assertIn('&amp; &gt; &quot; &#x27;', html)
        self.assertIn('&quot;&gt;&lt;img src=x onerror=alert(1)&gt;', html)
        self.assertIn('Тест &amp; тест', html)


if __name__ == '__main__':
    unittest.main()