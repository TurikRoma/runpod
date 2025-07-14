#!/bin/bash

echo "--- Starting Uvicorn Server in background ---"
uvicorn main:app --host 0.0.0.0 --port 8000 &

echo "--- Starting RunPod Handler ---"
# Запускаем handler и ждем его завершения
python3 -u handler.py 2>&1

# Получаем код завершения последней команды
EXIT_CODE=$?

# Проверяем, был ли код завершения НЕ нулевым (т.е. была ли ошибка)
if [ $EXIT_CODE -ne 0 ]; then
    echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
    echo "PYTHON HANDLER FAILED WITH EXIT CODE: $EXIT_CODE"
    echo "The container will sleep for 5 minutes for inspection."
    echo "Please check the logs above for the python traceback."
    echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
    sleep 300
fi