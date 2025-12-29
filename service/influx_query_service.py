# service/influx_query_service.py

import time
from influxdb import InfluxDBClient
from typing import List
from config import config
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class InfluxQueryService:
    """Service for querying InfluxDB."""

    def __init__(self, config_manager: config.ConfigManager):
        self.client = InfluxDBClient(
            config_manager.get_value('Influxdb_url'),
            config_manager.get_value('Influxdb_port'),
            config_manager.get_value('Influxdb_username'),
            config_manager.get_value('Influxdb_password'),
            'system_metrics'
        )

    def get_containers(self, namespace: str) -> List[str]:
        """Gets containers from InfluxDB."""
        containers = list(self.client.query(f"SHOW TAG VALUES WITH KEY = instance WHERE namespace = '{namespace}'"))
        if len(containers) < 1:
            logger.info("No data. Retrying...")
            time.sleep(3)
            return self.get_containers(namespace)
        else:
            return [list(i.values())[1] for i in containers[-1]]