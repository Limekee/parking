import requests
from typing import Dict, Any

# URL сервера API
API_BASE_URL = "https://sternly-prophetic-taipan.cloudpub.ru:443"
REQUEST_TIMEOUT = 10


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


if __name__ == "__main__":
    """Тестирование функции"""
    print("🚀 Тестирование update_parking_spaces")

    # Добавление мест
    print("\n➕ Добавление 5 мест в Восточный регион:")
    result = update_parking_spaces("Восточный регион", 3, "add")
    print(f"Результат: {result}")
