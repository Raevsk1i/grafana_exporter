# service/reflex_transfer_service.py
import requests
import logging
from typing import Dict, Any, Optional

from config import config

# Настройка логирования
logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)


class ReflexTransferService:
    """
    Сервис для отправки данных в Reflex Transfer через REST API.
    Все запросы — POST, URL берётся из config.reflex_transfer_url
    """

    def __init__(self):
        self.base_url = config.reflex_transfer_url.strip().rstrip("/")

        # Общие заголовки (можно расширить)
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def _post(self, endpoint: str, json_data: Dict[str, Any], timeout: int = 30) -> Dict[str, Any]:
        """
        Внутренний метод для отправки POST-запроса
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        logger.info(f"Отправка POST запроса: {url}")
        logger.debug(f"Payload: {json_data}")

        try:
            response = requests.post(
                url=url,
                json=json_data,
                headers=self.headers,
                timeout=timeout
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

    # === Примеры методов — дальше ты сам подредактируешь под свои нужды ===

    def send_transfer_request(self, transfer_id: str, amount: float, recipient: str) -> Dict[str, Any]:
        """
        Пример 1: Отправка запроса на перевод средств
        """
        payload = {
            "transfer_id": transfer_id,
            "amount": amount,
            "currency": "RUB",
            "recipient": recipient,
            "description": "Автоматический перевод из Confluence Tools"
        }
        return self._post("transfers", payload)

    def send_notification(self, title: str, message: str, tags: Optional[list] = None) -> Dict[str, Any]:
        """
        Пример 2: Отправка уведомления в систему
        """
        payload = {
            "title": title,
            "message": message,
            "level": "info",
            "tags": tags or []
        }
        return self._post("notifications", payload)

    def send_metrics_batch(self, metrics: list[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Пример 3: Отправка батча метрик
        """
        payload = {
            "batch_id": "auto_report_2025",
            "timestamp": "2025-12-27T12:00:00Z",
            "metrics": metrics
        }
        return self._post("metrics/batch", payload)

    def send_custom_event(self, event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Пример 4: Универсальный метод для кастомных событий
        """
        payload = {
            "event_type": event_type,
            "source": "confluence_auto_report",
            "data": data
        }
        return self._post("events", payload)


# Глобальный экземпляр для удобного использования
reflex_service = ReflexTransferService()