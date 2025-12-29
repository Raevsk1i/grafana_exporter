# workers/worker.py

from PyQt6.QtCore import QRunnable, pyqtSlot, pyqtSignal, QObject
import traceback

from PyQt6.QtWidgets import QProgressBar
from config import config
from service.influx_query_service import InfluxQueryService
from service.grafana_services.grafana_sceernshot_service import GrafanaScreenshotService
from service.confluence_services.confluence_page_service import ConfluencePageService
from service.confluence_services.confluence_attachment_service import ConfluenceAttachmentService
from utils.confluence_content_builder import load_template, get_table_from_page, create_xml_table, create_metrics_category_macro
from utils.confluence_graphics_sorter import categorize_graphics, sort_graphics_by_order

class WorkerSignals(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(str)
    result = pyqtSignal(object)
    progress = pyqtSignal(int)

class ProcessingWorker(QRunnable):
    def __init__(self, params: dict, progress_bar: QProgressBar):
        super().__init__()
        self.params = params
        self.signals = WorkerSignals()
        self.progress_bar = progress_bar

        # DI: Instantiate services with config
        self.influx_service = InfluxQueryService(config)
        self.grafana_service = GrafanaScreenshotService(config)
        self.page_service = ConfluencePageService(config)
        self.attachment_service = ConfluenceAttachmentService(config)

    @pyqtSlot()
    def run(self):
        try:
            # Extract params from GUI
            fp_code = self.params.get('fp_code')  # e.g., "VAT"
            namespace = fp_code.lower()  # Assume lowercase for queries
            start_time = self.params.get('from_dt')
            end_time = self.params.get('to_dt')
            page_name = self.params.get('page_name')
            append_mode = self.params.get('append_mode')
            test_name = self.params.get('test_name')  # From GUI

            # Derive template_path from test_name (assumed mapping)
            template_path = f"./tests/{test_name.replace(' ', '_').lower()}.html"  # e.g., "poisk_maksimuma.html"

            # Step 0: Determine/create page_id
            if append_mode:
                page_id = self.params.get('page_id')
                if not self.page_service.page_exists(page_id):
                    raise ValueError("Page ID does not exist for append mode.")
            else:
                space = self.params.get('space')
                parent_id = self.params.get('parent_id')
                page_id = self.page_service.create_new_page(space, page_name, parent_id)
                if not page_id:
                    raise ValueError("Failed to create new page.")

            self.signals.progress.emit(5)  # After page setup

            # Step 1: Get containers
            containers = self.influx_service.get_containers(namespace)
            self.signals.progress.emit(10)

            # Step 2: Make screenshots
            graphics = self.grafana_service.make_screenshots(containers, start_time, end_time, namespace)
            self.signals.progress.emit(40)

            # Step 3: Load template and categorize graphics
            template_content = load_template(template_path)
            system_metrics, software_metrics = categorize_graphics(graphics)
            self.signals.progress.emit(60)

            # Step 4: Build content
            category_macros = []
            if system_metrics:
                category_macros.append(create_metrics_category_macro("Системные метрики", system_metrics, sort_graphics_by_order))
            if software_metrics:
                category_macros.append(create_metrics_category_macro("Программные метрики", software_metrics, sort_graphics_by_order))
            new_content = "".join(category_macros)
            table_rows = get_table_from_page(self.page_service.confluence, config.get_value('Confluence_page_id_conf'), namespace)
            table_xml = create_xml_table(table_rows)
            final_content = template_content.replace('TOCHANGEFROMPYTHONEXPORTER', new_content).replace('PUTTABLECONFHEREPYTHONEXPORTER', table_xml)
            self.signals.progress.emit(80)

            # Step 5: Upload attachments
            self.attachment_service.upload_attachments(graphics, page_id)
            self.signals.progress.emit(90)

            # Step 6: Update/append page
            if append_mode:
                success = self.page_service.append_to_page(page_id, page_name, final_content)
            else:
                success = self.page_service.update_page_content(page_id, page_name, final_content)
            self.signals.progress.emit(100)

            self.signals.result.emit(success)
            self.signals.finished.emit()

        except Exception as e:
            error_trace = traceback.format_exc()
            print("Error in worker:", error_trace)
            self.signals.error.emit(error_trace)

        finally:
            self.progress_bar.hide()