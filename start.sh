#!/bin/bash

# Эта команда заставит скрипт немедленно завершиться, если любая команда вернет ошибку.
# Это очень важно для отладки.
set -e

echo "--- Starting Uvicorn Server in background ---"
uvicorn main:app --host 0.0.0.0 --port 8000 &

echo "--- Starting RunPod Handler in foreground ---"
# Теперь, если python3 handler.py упадет, мы увидим ошибку благодаря 'set -e'
python3 -u handler.py