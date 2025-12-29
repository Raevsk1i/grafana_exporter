# service/reflex_transfer_service.py
import json

import requests
import logging
import urllib3

from typing import Dict, Any
from config import config
from requests import request

# Настройка логирования
logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class ReflexTransferService:
    """
    Сервис для отправки данных в Reflex Transfer через REST API.
    Все запросы — POST, URL берётся из config.reflex_transfer_url
    """

    def __init__(self):
        self.base_url = config.get_value('reflex_transfer_url').strip().rstrip('/reflex-stubs/api/v1')

        # Общие заголовки (можно расширить)
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def _post(self, endpoint: str, json_data: Dict[str, Any] = None, timeout: int = 30) -> dict[str, str] | None | Any:
        """
        Внутренний метод для отправки POST-запроса
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        logger.info(f"Отправка POST запроса: {url}")
        logger.info(f"Payload: {json_data}")

        try:
            data = json.dumps(json_data)

            response = request(
                method="POST",
                url=url,
                data=data,
                headers=self.headers,
                timeout=timeout,
                verify=False,
                cert=('./resources/certs/tls.crt',
                      './resources/certs/tls.key')
            )

            if response.status_code in (200, 201):
                logger.info(f"Успешный ответ ({response.status_code}) от {endpoint}")
                try:
                    return response.json()
                except ValueError:
                    return {"status": "success", "raw_response": response.text}
            else:
                logger.error(f"Ошибка {response.status_code} от {endpoint}: {response.text}")
                response.raise_for_status()

        except requests.exceptions.Timeout:
            logger.error(f"Таймаут запроса к {endpoint}")
            raise
        except requests.exceptions.ConnectionError:
            logger.error(f"Ошибка подключения к {url}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Неизвестная ошибка запроса: {e}")
            raise


    def _get(self, endpoint: str, timeout: int = 30) -> dict[str, str] | None | Any:
        """
        Внутренний метод для отправки GET-запроса
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        logger.info(f"Отправка GET запроса: {url}")

        try:
            response = request(
                method="GET",
                url=url,
                headers=self.headers,
                timeout=timeout,
                verify=False,
                cert=('./resources/certs/tls.crt',
                      './resources/certs/tls.key')
            )

            if response.status_code in (200, 201):
                logger.info(f"Успешный ответ ({response.status_code}) от {endpoint}")
                try:
                    return response.json()
                except ValueError:
                    return {"status": "success", "raw_response": response.text}
            else:
                logger.error(f"Ошибка {response.status_code} от {endpoint}: {response.text}")
                response.raise_for_status()

        except requests.exceptions.Timeout:
            logger.error(f"Таймаут запроса к {endpoint}")
            raise
        except requests.exceptions.ConnectionError:
            logger.error(f"Ошибка подключения к {url}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Неизвестная ошибка запроса: {e}")
            raise

    def send_create_transfer_request(self, namespace: str) -> Dict[str, Any]:
        """
        Запрос на создание регулярного трансфера метрик
        """
        payload = {
            "namespace": f"{namespace}",
        }
        return self._post("create/transfer", payload)

    def send_stop_transfer_request(self, namespace: str) -> Dict[str, Any]:
        """
        Запрос на остановку трансфера по namespace
        """
        payload = {
            "namespace": f"{namespace}",
        }
        return self._post("stop/transfer", payload)

    def send_get_transfers_request(self) -> Dict[str, Any]:
        """
        Запрос на получение всех активных трансферов
        """
        return self._get("get/transfer")

    def send_start_transfer_from_to_request(self, namespace: str, from_time: str, to_time: str) -> Dict[str, Any]:
        """
        Запрос на создание трансфера метрик from-to
        """
        payload = {
            "namespace": f"{namespace}",
        }
        return self._post(f"transfer/from/{from_time}/to/{to_time}", payload)

    def send_recreate_database_request(self):
        """
        Запрос на пересоздание базы данных influx
        """
        return self._post("recreate/database", {})

    # Требуется добавить функциональность в reflex-transfer
    def send_delete_instance_request(self, namespace: str):
        """
        Запрос на удаление всех instance по коду ФП
        """
        payload = {
            "namespace": f"{namespace}",
        }
        return self._post("delete/instance", payload)

# Глобальный экземпляр для удобного использования
reflex_service = ReflexTransferService()