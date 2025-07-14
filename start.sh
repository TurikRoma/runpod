#!/bin/bash
set -e

echo "--- Starting Uvicorn Server in background ---"
uvicorn main:app --host 0.0.0.0 --port 8000 &

echo "--- Starting RunPod Handler in foreground (with stderr redirection) ---"
# Это ключевое изменение: 2>&1 перенаправляет поток ошибок в стандартный вывод
python3 -u handler.py 2>&1