FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      build-essential git python3-dev libffi-dev curl \
      ffmpeg libgl1 libglib2.0-0 libsm6 libxrender1 libxext6 \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code into image
COPY . .

# --- КЛЮЧЕВОЕ ИЗМЕНЕНИЕ: СКАЧИВАЕМ МОДЕЛИ ВО ВРЕМЯ СБОРКИ ---
# Этот шаг займет много времени при сборке, но сделает запуск воркера почти мгновенным.
# Мы вызываем наш скрипт в режиме "только скачать".
# Устанавливаем переменные окружения, которые использует huggingface_hub
ENV HF_HOME=/app/models_cache
ENV HF_HUB_CACHE=/app/models_cache
ENV HUGGINGFACE_HUB_CACHE=/app/models_cache
RUN python3 -c "from model_loader import load_models; load_models(download_only=True)"
# ---------------------------------------------------------------

# Debug: list files to see the cache
RUN echo "FILES IN /app:" && ls -R /app 

# Make the start script executable
RUN chmod +x start.sh

# Default command
CMD ["./start.sh"]