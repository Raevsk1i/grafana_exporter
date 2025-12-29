# service/grafana_screenshot_service.py

import requests
import os
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from typing import Dict, List
from utils.grafana_url_builder import build_grafana_url

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class GrafanaScreenshotService:
    """Service for fetching and saving Grafana screenshots."""

    def __init__(self, config_manager):
        self.max_workers = int(config_manager.get_value('Grafana_max_workers', '10'))
        self.request_delay = float(config_manager.get_value('Grafana_request_delay', '0.5'))
        self.max_retries = int(config_manager.get_value('Grafana_max_retries', '3'))
        self.grafana_token = config_manager.get_value('Grafana_api_token')
        host = config_manager.get_value('Grafana_host')
        port = config_manager.get_value('Grafana_port')
        uid = config_manager.get_value('Grafana_dashboard_uid')
        slug = config_manager.get_value('Grafana_dashboard_slug')
        self.base_dashboard_url = f"{host}:{port}/render/d-solo/{uid}/{slug}"

    def fetch_panel_screenshot(self, url: str) -> BytesIO:
        """Fetches a single screenshot with retries."""
        headers = {"Authorization": f"Bearer {self.grafana_token}"}
        for attempt in range(self.max_retries):
            try:
                response = requests.get(url, headers=headers, timeout=60)
                if response.status_code == 200:
                    return BytesIO(response.content)
                elif response.status_code == 429:
                    wait_time = (attempt + 1) * 10
                    logger.warning(f"Rate limit. Waiting {wait_time}s")
                    time.sleep(wait_time)
                elif response.status_code >= 500:
                    wait_time = (attempt + 1) * 5
                    logger.warning(f"Server error {response.status_code}. Waiting {wait_time}s")
                    time.sleep(wait_time)
                else:
                    response.raise_for_status()
            except requests.exceptions.RequestException as e:
                logger.warning(f"Request failed (attempt {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep((attempt + 1) * 5)
        raise Exception(f"Failed after {self.max_retries} attempts")

    def save_graphic_to_dir(self, content: bytes, directory: str, filename: str):
        """Saves screenshot to file."""
        os.makedirs(directory, exist_ok=True)
        filepath = os.path.join(directory, filename)
        with open(filepath, 'wb') as file:
            file.write(content)

    def process_single_screenshot(self, task: Dict) -> tuple:
        """Processes a single screenshot task."""
        url = build_grafana_url(task['namespace'], task['panel_id'], task['container'], task['start_time'], task['end_time'], self.base_dashboard_url)
        try:
            image_content = self.fetch_panel_screenshot(url)
            filename = f"{task['container']}-{task['graphic_name']}.png"
            self.save_graphic_to_dir(image_content.getvalue(), task['namespace'], filename)
            filepath = f"{task['namespace']}/{filename}"
            logger.info(f"Saved: {filepath}")
            return task['container'], task['graphic_name'], filepath, None
        except Exception as error:
            logger.error(f"Failed {task['container']}/{task['graphic_name']}: {error}")
            return task['container'], task['graphic_name'], None, error

    def make_screenshots(self, containers: List[str], start_time: str, end_time: str, namespace: str) -> Dict[str, Dict[str, str]]:
        """Generates screenshots in batches."""
        os.makedirs(namespace, exist_ok=True)
        tasks = self._create_screenshot_tasks(containers, start_time, end_time, namespace)
        results = {container: {} for container in containers}
        errors = []
        batch_size = min(self.max_workers * 2, 10)
        for i in range(0, len(tasks), batch_size):
            batch = tasks[i:i + batch_size]
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = [executor.submit(self.process_single_screenshot, task) for task in batch]
                for future in as_completed(futures):
                    container, graphic_name, filepath, error = future.result()
                    if error:
                        errors.append(f"{container}/{graphic_name}: {error}")
                    elif filepath:
                        results[container][graphic_name] = filepath
            if i + batch_size < len(tasks):
                time.sleep(self.request_delay)
        if errors:
            logger.warning(f"{len(errors)} errors occurred")
        return {k: v for k, v in results.items() if v}

    def _create_screenshot_tasks(self, containers: List[str], start_time: str, end_time: str, namespace: str) -> List[Dict]:
        """Creates tasks for screenshots (internal)."""
        panel_ids = {  # From original
            'cpu-usage-percent': 5, 'cpu-usage-limit-(millicores)': 6, 'cpu-throttled-(millicores)': 43,
            # ... (all others as in original)
            'threads-count': 54
        }
        excpanel = {'heap-(bytes)', 'heap-per-pool-(bytes)', 'nonHeap-per-pool-(bytes)', 'metaspace-(bytes)', 'gc-collection-count-time', 'threads-count'}
        tasks = []
        for container in containers:
            for graphic_name, panel_id in panel_ids.items():
                if (container.__contains__('ingress') or container.__contains__('egress')) and graphic_name in excpanel:
                    continue
                tasks.append({
                    'container': container, 'graphic_name': graphic_name, 'panel_id': panel_id,
                    'namespace': namespace, 'start_time': start_time, 'end_time': end_time
                })
        return tasks