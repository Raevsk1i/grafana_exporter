# python ConfluenceUtils

import os
import time
import urllib3

from bs4 import BeautifulSoup
from dotenv import find_dotenv, load_dotenv
from atlassian import Confluence
from utils.GrafanaUtils import make_screenshots
from pathlib import Path
from typing import List, Dict

# Загрузка переменных окружения
load_dotenv(find_dotenv('../.env'))
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class ConfluenceReporter:
    """Класс для работы с созданием отчетов в Confluence."""

    def __init__(self):
        self.template_path = None
        self.confluence = Confluence(
            url=os.getenv('CONFLUENCE_URL'),
            token=os.getenv('CONFLUENCE_TOKEN'),
            verify_ssl=False
        )

        # Определяем общий порядок ВСЕХ графиков для всех типов метрик
        # TODO -> изменять в случае появления новых графиков
        self.all_metrics_order = [
            # Системные метрики
            'cpu-usage-percent', 'cpu-usage-limit-(millicores)', 'cpu-throttled-(millicores)',
            'ram-usage-percent', 'ram-usage-limit-(bytes)', 'disk-total-avail-used-(bytes)',
            'disk-read-write-(bytes)', 'disk-read-write-(ops)', 'traffic-in-out-(bytes)',

            # Программные метрики
            'heap-(bytes)', 'heap-per-pool-(bytes)', 'nonHeap-per-pool-(bytes)',
            'metaspace-(bytes)', 'gc-collection-count-time', 'threads-count'
        ]

    def _load_template(self) -> str:
        """Загружает шаблон страницы из файла."""
        path = f'./tests/{self.template_path}'
        if not Path(path).exists():
            raise FileNotFoundError(f"Шаблон не найден: {path}")

        with open(path, "r", encoding="utf-8") as file:
            return file.read()

    def _sort_graphics_by_order(self, graphics: Dict[str, str]) -> List[tuple]:
        """
        Сортирует все графики согласно общему порядку.

        Args:
            graphics: Словарь {название_графика: путь_к_файлу}

        Returns:
            List[tuple]: Отсортированный список пар (название_графика, путь_к_файлу)
        """
        sorted_graphics = []
        remaining_graphics = list(graphics.items())

        # Сначала добавляем графики в указанном порядке
        for metric_name in self.all_metrics_order:
            matched_graphics = []
            for panel_name, screenshot_path in remaining_graphics:
                if metric_name in panel_name.lower():
                    matched_graphics.append((panel_name, screenshot_path))

            # Добавляем найденные графики в результат
            sorted_graphics.extend(matched_graphics)

            # Удаляем добавленные графики из оставшихся
            for graphic in matched_graphics:
                if graphic in remaining_graphics:
                    remaining_graphics.remove(graphic)

        # Затем добавляем все оставшиеся графики, отсортированные по имени
        remaining_graphics.sort(key=lambda x: x[0].lower())
        sorted_graphics.extend(remaining_graphics)

        return sorted_graphics

    def _get_table_from_page(self, page_id_n, namespace: str):
        """
        Извлекает таблицу с страницы Confluence

        Args:
            page_id_n: ID страницы
            namespace: название неймспейса ФП

        Returns:
            rows list: лист строк таблицы
        """
        confluence = Confluence(
            url=os.getenv('CONFLUENCE_URL'),
            token=os.getenv('CONFLUENCE_TOKEN'),
            verify_ssl=False
        )
        # Получаем страницу с расширенной информацией о body
        page = confluence.get_page_by_id(page_id_n, expand='body.storage')

        # Извлекаем HTML содержимое
        html_content = page['body']['storage']['value']

        # Парсим HTML с помощью BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')

        # Находим все таблицы
        tables = soup.find_all('table')

        if not tables:
            print("На странице не найдено таблиц")
            return None

        if 0 >= len(tables):
            print(f"Таблица с индексом 0 не найдена. Всего таблиц: {len(tables)}")
            return None

        # Извлекаем нужную таблицу
        table = tables[0]

        # Парсим таблицу в DataFrame
        rows = []
        for row in table.find_all('tr')[1:]:
            if not row.find_all('td')[0].__contains__(namespace.upper()):
                continue
            cells = []
            for v in row.find_all('td')[1:]:
                cells.append(v)
            rows.append(cells)

        return rows

    def _create_panel_content(self, graphics: Dict[str, str]) -> str:
        """
        Создает HTML-контент для панелей графиков с общей сортировкой.
        """
        panels_html = []

        # Сортируем все графики по общему порядку
        sorted_graphics = self._sort_graphics_by_order(graphics)

        for panel_name, screenshot_path in sorted_graphics:
            # Добавляем заголовок панели
            panels_html.append(f"<h3>{panel_name}</h3>")

            # Добавляем изображение
            filename = Path(screenshot_path).name
            image_macro = (
                f'<br /><ac:image ac:height="400">'
                f'<ri:attachment ri:filename="{filename}" />'
                f'</ac:image><br /><br />'
            )
            panels_html.append(image_macro)

        return "".join(panels_html)

    def _create_service_expand(self, service_name: str, graphics: Dict[str, str]) -> str:
        """Создает ui-expand для отдельного сервиса с его графиками."""
        panels_content = self._create_panel_content(graphics)

        service_macro = (
            '<ac:structured-macro ac:name="ui-expand" ac:schema-version="1">'
            f'<ac:parameter ac:name="title">{service_name}</ac:parameter>'
            f'<ac:rich-text-body><p>{panels_content}</p></ac:rich-text-body>'
            '</ac:structured-macro>'
        )

        return service_macro

    def _create_metrics_category_macro(self, category_name: str, services_graphics: Dict[str, Dict[str, str]]) -> str:
        """
        Создает макрос для категории метрик (системные или программные).
        Внутри содержит ui-expand для каждого сервиса.
        """
        service_expands_html = []

        # Сортируем сервисы по имени для consistency
        sorted_services = sorted(services_graphics.items())

        for service_name, graphics in sorted_services:
            service_macro = self._create_service_expand(service_name, graphics)
            service_expands_html.append(service_macro)

        services_content = "".join(service_expands_html)

        # Создаем внешний ui-expand для категории метрик
        category_macro = (
            '<ac:structured-macro ac:name="ui-expand" ac:schema-version="1">'
            f'<ac:parameter ac:name="title">{category_name}</ac:parameter>'
            f'<ac:rich-text-body><p>{services_content}</p></ac:rich-text-body>'
            '</ac:structured-macro>'
        )

        return category_macro

    def _categorize_graphics(self, graphics: Dict[str, Dict[str, str]]) -> tuple:
        """
        Разделяет графики на системные и программные метрики.

        Returns:
            tuple: (system_metrics, software_metrics)
        """
        system_metrics = {}
        software_metrics = {}

        software_keywords = ['heap', 'metaspace', 'gc', 'jvm', 'thread', 'class', 'compilation']

        for container, container_graphics in graphics.items():
            system_metrics[container] = {}
            software_metrics[container] = {}

            for panel_name, screenshot_path in container_graphics.items():
                panel_name_lower = panel_name.lower()

                # Проверяем, содержит ли название панели ключевые слова программных метрик
                if any(keyword in panel_name_lower for keyword in software_keywords):
                    software_metrics[container][panel_name] = screenshot_path
                else:
                    system_metrics[container][panel_name] = screenshot_path

            # Удаляем пустые записи
            if not system_metrics[container]:
                del system_metrics[container]
            if not software_metrics[container]:
                del software_metrics[container]

        return system_metrics, software_metrics

    def _upload_attachments(self, graphics: Dict[str, Dict[str, str]], page_id: str) -> List[str]:
        """Загружает все вложения на страницу Confluence."""
        file_paths = []

        for container, container_graphics in graphics.items():
            for screenshot_path in container_graphics.values():
                try:
                    # Небольшая задержка для избежания rate limiting
                    time.sleep(0.4)

                    self.confluence.attach_file(
                        screenshot_path,
                        page_id=page_id,
                        title=f"Графики {container}"
                    )
                    file_paths.append(screenshot_path)

                except Exception as error:
                    print(f"Ошибка при загрузке вложения {screenshot_path}: {error}")

        return file_paths

    def _get_current_content(self, page_id: str) -> str:
        """
        Получает текущее содержимое страницы Confluence.
        Важно использовать правильное представление (representation) 'storage'.
        """
        try:
            current_page = self.confluence.get_page_by_id(page_id, expand='body.storage')
            current_content = current_page.get('body', {}).get('storage', {}).get('value', '')
            return current_content
        except Exception as error:
            print(f"Ошибка при получении содержимого страницы: {error}")
            return ""

    def _update_page_content(self, page_id: str, title: str, new_content: str) -> bool:
        """
        Обновляет страницу, добавляя новый контент к существующему.
        Это надежная альтернатива append_page.
        """
        try:
            # 1. Получить текущий контент
            current_content = self._get_current_content(page_id)

            # 2. Объединить контент
            combined_content = current_content + new_content

            # 3. Обновить страницу
            result = self.confluence.update_page(
                page_id=page_id,
                title=title,
                body=combined_content,  # Используется 'body' для полного содержимого
                representation='storage',
                minor_edit=False
            )

            return result is not None

        except Exception as error:
            print(f"Ошибка при обновлении страницы: {error}")
            return False

    def _append_to_page(self, page_id: str, title: str, append_content: str) -> bool:
        """
        Пытается использовать метод append_page.
        Используйте параметр `append_body` для передачи добавляемого контента.
        """
        try:
            result = self.confluence.append_page(
                page_id=page_id,
                title=title,
                append_body=append_content,  # Правильный параметр для добавления
                representation='storage',
                minor_edit=False
            )
            return result is not None
        except Exception as error:
            print(f"Ошибка при добавлении контента (append_page): {error}")
            return False

    def create_new_page(self, space: str, title: str, parent_page: str = None) -> str:
        """
        Создает новую страницу в Confluence.

        Args:
            space: Ключ пространства
            title: Заголовок страницы
            parent_page: ID родительской страницы (опционально)

        Returns:
            str: ID созданной страницы или пустая строка при ошибке
        """

        try:
            result = self.confluence.create_page(
                space=space,
                title=title,
                body="",  # Начинаем с пустой страницы
                parent_id=parent_page,
                type='page'
            )
            return result.get('id', '') if result else ''
        except Exception as error:
            print(f"Ошибка при создании страницы: {error}")
            return ''

    def page_exists(self, page_id: str) -> bool:
        """
        Проверяет существование страницы по ID.

        Args:
            page_id: ID страницы

        Returns:
            bool: True если страница существует
        """
        try:
            page = self.confluence.get_page_by_id(page_id)
            return page is not None
        except Exception:
            return False

    def create_xml_table(self, rows):
        res = "<table><colgroup> <col/> <col/> <col/> <col/> <col/> <col/> </colgroup>"
        headers = ['Pod', 'Distribution version', 'Install date', 'Status', 'Resources', 'Java Opts']
        res += "<tbody>"
        res += "<tr>"
        for header in headers:
            res += f"<th><p>{header}</p></th>"
        res += "</tr>"

        for row in rows:
            res += "<tr>"
            for v in row:
                res += str(v)
            res += "</tr>"
        res += '</tbody></table>'
        return res

    def get_page_id_by_title(self, space: str, title: str) -> str:
        """
        Находит ID страницы по заголовку и пространству.

        Args:
            space: Ключ пространства
            title: Заголовок страницы

        Returns:
            str: ID страницы или пустая строка если не найдена
        """
        try:
            pages = self.confluence.get_page_id(space, title)
            return pages if pages else ''
        except Exception as error:
            print(f"Ошибка при поиске страницы: {error}")
            return ''

    def delete_page(self, page_id: str) -> bool:
        """
        Удаляет страницу по ID.

        Args:
            page_id: ID страницы

        Returns:
            bool: True если удаление успешно
        """
        try:
            self.confluence.remove_page(page_id)
            return True
        except Exception as error:
            print(f"Ошибка при удалении страницы: {error}")
            return False

    def get_page_attachments(self, page_id: str) -> List[Dict]:
        """
        Получает список вложений страницы.

        Args:
            page_id: ID страницы

        Returns:
            List[Dict]: Список вложений
        """
        try:
            attachments = self.confluence.get_attachments_from_content(page_id)
            return attachments.get('results', [])
        except Exception as error:
            print(f"Ошибка при получении вложений: {error}")
            return []

    def delete_attachment(self, page_id: str, filename: str) -> bool:
        """
        Удаляет вложение со страницы.

        Args:
            page_id: ID страницы
            filename: Имя файла для удаления

        Returns:
            bool: True если удаление успешно
        """
        try:
            self.confluence.delete_attachment(page_id, filename)
            return True
        except Exception as error:
            print(f"Ошибка при удалении вложения: {error}")
            return False

    def make_report(
            self,
            containers: List[str],
            path_to_test: str,
            start_time: str,
            end_time: str,
            namespace: str,
            page_id: str,
            page_name: str,
            use_append_method: bool = False
    ) -> bool:
        """
        Создает отчет в Confluence с графиками для указанных контейнеров.

        Args:
            containers: Список контейнеров
            path_to_test: Название теста
            start_time: Время начала периода
            end_time: Время окончания периода
            namespace: Пространство имен
            page_id: ID страницы Confluence
            page_name: Название страницы
            use_append_method: Если True, использует append_page. Если False, использует надежное обновление.
        """

        self.template_path = Path(path_to_test)

        try:
            # Получаем графики
            print("Создание скриншотов графиков...")
            graphics = make_screenshots(containers, start_time, end_time, namespace)

            # Загружаем шаблон
            print("Загрузка шаблона страницы...")
            template_content = self._load_template()

            # Разделяем графики на системные и программные метрики
            print("Разделение графиков на категории...")
            system_metrics, software_metrics = self._categorize_graphics(graphics)

            # Создаем контент для Confluence
            print("Формирование контента страницы...")
            category_macros = []

            # Добавляем макрос для системных метрик, если есть
            if system_metrics:
                system_macro = self._create_metrics_category_macro("Системные метрики", system_metrics)
                category_macros.append(system_macro)

            # Добавляем макрос для программных метрик, если есть
            if software_metrics:
                software_macro = self._create_metrics_category_macro("Программные метрики", software_metrics)
                category_macros.append(software_macro)

            new_content = "".join(category_macros)
            table = self._get_table_from_page(os.getenv('CONFLUENCE_PAGE_ID_CONF'), namespace)

            final_content = template_content.replace('TOCHANGEFROMPYTHONEXPORTER', new_content)
            final_content = final_content.replace('PUTTABLECONFHEREPYTHONEXPORTER', self.create_xml_table(table))

            # Загружаем вложения
            print("Загрузка вложений в Confluence...")
            self._upload_attachments(graphics, page_id)

            # Обновляем страницу в Confluence
            print("Обновление страницы Confluence...")
            if use_append_method:
                success = self._append_to_page(page_id, page_name, final_content)
            else:
                success = self._update_page_content(page_id, page_name, final_content)

            if success:
                print("Отчет успешно создан!")
            else:
                print("Ошибка при создании отчета!")

            return success

        except FileNotFoundError as error:
            print(f"Ошибка: {error}")
            return False
        except Exception as error:
            print(f"Неожиданная ошибка при создании отчета: {error}")
            return False


# Функция для обратной совместимости
def make_report(containers: List[str], path_to_test: str, start_time: str, end_time: str,
                namespace: str, page_id: str, page_name: str) -> bool:
    reporter = ConfluenceReporter()
    # По умолчанию используем надежный метод,
    return reporter.make_report(containers, path_to_test, start_time, end_time, namespace, page_id, page_name,
                                use_append_method=False)


# Дополнительные функции для удобства
def create_confluence_page(space: str, title: str, parent_page: str = None) -> str:
    """
    Создает новую страницу в Confluence.

    Args:
        space: Ключ пространства
        title: Заголовок страницы
        parent_page: ID родительской страницы (опционально)

    Returns:
        str: ID созданной страницы
    """
    reporter = ConfluenceReporter()
    return reporter.create_new_page(space, title, parent_page)

def find_page_id(space: str, title: str) -> str:
    """
    Находит ID страницы по заголовку и пространству.

    Args:
        space: Ключ пространства
        title: Заголовок страницы

    Returns:
        str: ID страницы
    """
    reporter = ConfluenceReporter()
    return reporter.get_page_id_by_title(space, title)