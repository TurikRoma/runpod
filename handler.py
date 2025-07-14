import os
import requests
import runpod

# URL нашего FastAPI сервера внутри контейнера
LOCAL_URL = "http://127.0.0.1:8000"

def handler(job):
    """
    Эта функция-обработчик вызывается RunPod для каждого запроса.
    """
    # Получаем детали запроса из входных данных от RunPod
    job_input = job.get('input', {})
    
    http_method = job_input.get('http_method', 'GET').upper()
    path = job_input.get('path', '/')
    
    # Отправляем локальный запрос на наш FastAPI сервер
    try:
        response = requests.request(
            http_method,
            f"{LOCAL_URL}{path}",
            headers=job_input.get('headers', {}),
            json=job_input.get('body', None), # Используем json, если тело запроса - это JSON
            timeout=300 # Таймаут в 5 минут
        )
        response.raise_for_status() # Вызовет ошибку, если FastAPI вернет код > 400
        
        # Возвращаем результат (JSON) обратно системе RunPod
        return response.json()

    except requests.exceptions.RequestException as e:
        # В случае ошибки возвращаем текст ошибки
        return {"error": f"Failed to request local server: {e}"}

# Запускаем serverless-воркер RunPod, который будет вызывать нашу функцию handler
runpod.serverless.start({"handler": handler})