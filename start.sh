#!/bin/bash
set -e

echo "--- STARTING SCRIPT ---"

echo "--- Verifying python installation ---"
which python3
python3 --version

echo "--- Verifying Uvicorn (module) installation ---"
python3 -m uvicorn --version

# Start Uvicorn in background, redirecting its logs directly to stdout/stderr
# --log-level debug - полезно для отладки
echo "--- Starting Uvicorn Server in background ---"
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --log-level debug & 

# --- Убираем цикл ожидания Uvicorn'а ---
# Handler.py будет сам пытаться подключиться и вернет ошибку, если Uvicorn не готов

# Run the RunPod handler in foreground
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