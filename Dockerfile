FROM python:3.10-slim

WORKDIR /app

# Install system packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      build-essential git python3-dev libffi-dev curl \
      ffmpeg libgl1 libglib2.0-0 libsm6 libxrender1 libxext6 \
      libgomp1 libsndfile1 unzip \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Update pip and install build tools
RUN pip install --upgrade pip setuptools wheel

# --- КЭШИРОВАНИЕ ---
# Создаем папки для кэша Hugging Face и InsightFace.
# Используем ENV для единообразия путей.
ENV HF_HOME /root/.cache/huggingface
RUN mkdir -p $HF_HOME/hub \
             /root/.insightface/models

# Предзагрузка модели insightface (buffalo_l)
RUN echo "Downloading insightface buffalo_l model..." && \
    curl -L https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip -o /root/.insightface/models/buffalo_l.zip && \
    echo "Extracting insightface buffalo_l model..." && \
    unzip /root/.insightface/models/buffalo_l.zip -d /root/.insightface/models && \
    rm /root/.insightface/models/buffalo_l.zip

# --- УСТАНОВКА PYTHON ЗАВИСИМОСТЕЙ ---
# Копируем requirements.txt и устанавливаем зависимости ДО кода приложения для лучшего кэширования слоев
COPY requirements.txt .
# Добавляем controlnet_aux[full] для установки всех зависимостей OpenposeDetector
RUN pip install --no-cache-dir -r requirements.txt \
    opencv-python-headless \
    controlnet_aux[full]

# --- ПРЕДЗАГРУЗКА МОДЕЛЕЙ HUGGING FACE ---
# Копируем скрипт для предзагрузки и запускаем его.
# Это заменяет небезопасные команды hf_hub_download для отдельных файлов.
COPY pre_download_models.py .
RUN python3 pre_download_models.py

# --- КОПИРОВАНИЕ КОДА ПРИЛОЖЕНИЯ ---
COPY . .

# Проверка, что все скопировалось (опционально)
RUN ls -R /app

# Делаем скрипт запуска исполняемым
RUN chmod +x start.sh

# Команда по умолчанию
CMD ["./start.sh"]