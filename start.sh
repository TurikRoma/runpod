#!/bin/bash
set -e

echo "--- STARTING SCRIPT ---"

# Verify Python
echo "--- Verifying python installation ---"
which python3
python3 --version

echo "--- Verifying Uvicorn (module) installation ---"
python3 -m uvicorn --version

# Start Uvicorn in background, logging to file
echo "--- Starting Uvicorn Server in background ---"
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --log-level debug > uvicorn.log 2>&1 &

# Wait until Uvicorn responds
echo "⏳ Waiting for Uvicorn to initialize…"
for i in {1..10}; do
  if curl -s http://127.0.0.1:8000/ > /dev/null; then
    echo "✅ Uvicorn is up!"
    break
  fi
  printf "."
  sleep 1
done

echo "📄 UVicorn startup log (first 50 lines):"
head -n 50 uvicorn.log || true

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