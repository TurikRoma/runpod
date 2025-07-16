import os
import requests
import runpod
import time  # <-- Добавляем импорт

LOCAL_URL = "http://127.0.0.1:8000"

def wait_for_server():
    """
    Ждет, пока локальный FastAPI сервер не станет доступным.
    """
    print("Waiting for local server to be ready...")
    # Увеличиваем таймаут до 240 секунд (4 минуты)
    # Это должно быть достаточно для загрузки моделей с диска
    start_time = time.time()
    while time.time() - start_time < 240: # <--- УВЕЛИЧЕНО
        try:
            # Используем корневой эндпоинт FastAPI, который не требует моделей
            requests.get(f"{LOCAL_URL}/", timeout=1) 
            print("Local server is READY!")
            return True
        except requests.ConnectionError:
            print(f"Server not ready yet, waiting... (elapsed: {int(time.time() - start_time)}s)")
            time.sleep(2) # Проверяем каждые 2 секунды
    
    print("CRITICAL: Local server did not start in 240 seconds.")
    return False


# --- ИЗМЕНЕНИЕ: Мы ждем сервер только один раз ---
server_ready = wait_for_server()


def handler(job):
    if not server_ready:
        return {"error": "Local FastAPI server failed to start."}

    job_input = job.get('input', {})
    http_method = job_input.get('http_method', 'GET').upper()
    path = job_input.get('path', '/')

    print(f"Received job: Method={http_method}, Path={path}")

    try:
        response = requests.request(
            http_method,
            f"{LOCAL_URL}{path}",
            headers=job_input.get('headers', {}),
            json=job_input.get('body', None),
            # Таймаут RunPod по умолчанию 5 минут (300с), ставим чуть меньше
            timeout=290 
        )
        response.raise_for_status()
        print(f"Request to local server successful, status: {response.status_code}")
        # Проверяем, что ответ - это валидный JSON
        try:
            return response.json()
        except requests.exceptions.JSONDecodeError:
            print(f"Error: Response is not valid JSON. Response text: {response.text[:500]}")
            return {"error": "Response from FastAPI was not valid JSON.", "response_text": response.text[:500]}

    except requests.exceptions.RequestException as e:
        print(f"Error requesting local server: {e}")
        return {"error": f"Failed to request local server: {e}"}
    except Exception as e:
        print(f"An unexpected error occurred in handler: {e}")
        return {"error": f"An unexpected error occurred: {e}"}

runpod.serverless.start({"handler": handler})