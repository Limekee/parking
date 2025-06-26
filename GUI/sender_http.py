import requests
from typing import Dict, Any
import json
import threading
import time

API_BASE_URL = "https://sternly-prophetic-taipan.cloudpub.ru:443"
REQUEST_TIMEOUT = 10
CACHE_LOCK = threading.Lock()
regions_cache = {"data": [], "timestamp": 0}
CACHE_TTL = 5  # секунд


def fetch_regions_data():
    """Получает данные регионов с сервера и кеширует их"""
    url = f"{API_BASE_URL}/regions"

    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        if response.status_code == 200:
            with CACHE_LOCK:
                regions_cache["data"] = response.json()
                regions_cache["timestamp"] = time.time()
            return True
        return False
    except Exception:
        return False


def get_cached_regions():
    """Возвращает кешированные данные регионов"""
    with CACHE_LOCK:
        # Проверяем актуальность кеша
        if time.time() - regions_cache["timestamp"] > CACHE_TTL:
            # Обновляем кеш в фоновом режиме
            threading.Thread(target=fetch_regions_data, daemon=True).start()
        return regions_cache["data"].copy()


def update_parking_spaces(region: str, delta: int, operation: str) -> Dict[str, Any]:
    """
    Отправляет HTTP-запрос для изменения количества парковочных мест в регионе

    Args:
        region (str): Название региона
        delta (int): Количество мест для добавления или удаления
        operation (str): Операция - 'add' для добавления, 'remove' для удаления

    Returns:
        dict: Ответ от сервера или информация об ошибке
    """
    # Проверяем корректность параметров
    if not isinstance(region, str) or not region.strip():
        return {"success": False, "error": "Region must be a non-empty string"}

    if not isinstance(delta, int) or delta <= 0:
        return {"success": False, "error": "Delta must be a positive integer"}

    if operation not in ["add", "remove"]:
        return {"success": False, "error": "Operation must be 'add' or 'remove'"}

    # Формируем URL и данные
    url = f"{API_BASE_URL}/regions/{region}/{operation}"
    payload = {"delta": delta}

    try:
        response = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)

        if response.status_code == 200:
            return {
                "success": True,
                "data": response.json(),
                "message": f"Successfully {operation}ed {delta} spaces in region '{region}'",
            }
        else:
            try:
                error_message = response.json().get("error", "Unknown error")
            except:
                error_message = f"HTTP {response.status_code}: {response.text}"

            return {
                "success": False,
                "status_code": response.status_code,
                "error": error_message,
            }

    except requests.exceptions.ConnectionError:
        return {"success": False, "error": f"Connection failed to {API_BASE_URL}"}
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": f"Request timed out after {REQUEST_TIMEOUT} seconds",
        }
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"Request failed: {str(e)}"}


def get_regions_status():
    """
    Получает текущий статус всех регионов

    Returns:
        dict: Список регионов с их статусом или информация об ошибке
    """
    url = f"{API_BASE_URL}/regions"

    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT)

        if response.status_code == 200:
            try:
                response_data = response.json()
            except json.JSONDecodeError:
                response_data = {"message": "No data available"}

            return {"success": True, "data": response_data}
        else:
            try:
                error_data = response.json()
                error_message = error_data.get("error", "Failed to get regions status")
            except json.JSONDecodeError:
                error_message = f"HTTP {response.status_code}: {response.text}"

            return {
                "success": False,
                "status_code": response.status_code,
                "error": error_message,
            }

    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "error": f"Connection failed. Make sure the server is running on {API_BASE_URL}",
        }
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": f"Request timed out after {REQUEST_TIMEOUT} seconds",
        }
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"Request failed: {str(e)}"}

# Загружаем данные при старте
fetch_regions_data()
