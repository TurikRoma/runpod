#!/bin/bash
set -e

echo "--- STARTING SCRIPT ---"

echo "--- Verifying python installation ---"
which python3
python3 --version

echo "--- Verifying Uvicorn (module) installation ---"
python3 -m uvicorn --version

# Start Uvicorn in background. Its logs will go directly to stdout/stderr of the container.
# --log-level debug - полезно для отладки
echo "--- Starting Uvicorn Server in background ---"
# Запускаем Uvicorn, его логи пойдут в основной поток.
# Если Uvicorn падает, мы увидим его ошибку.
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --log-level debug & 

# Run the RunPod handler in foreground.
# Это основной процесс контейнера. Если он завершится, контейнер остановится.
echo "--- Starting RunPod Handler in foreground ---"
python3 -u handler.py 2>&1
EXIT_CODE=$?
if [ $EXIT_CODE -ne 0 ]; then
    echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
    echo "PYTHON HANDLER FAILED WITH EXIT CODE: $EXIT_CODE"
    echo "The container will sleep for 5 minutes for inspection."
    echo "Please check the logs above for the python traceback."
    echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
    sleep 300
fi