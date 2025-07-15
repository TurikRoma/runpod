FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system packages for C-extension builds, Git, Curl, image/video libs, unzip
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      build-essential git python3-dev libffi-dev curl \
      ffmpeg libgl1 libglib2.0-0 libsm6 libxrender1 libxext6 \
      libgomp1 libsndfile1 unzip \ 
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# --- КЛЮЧЕВОЕ ИЗМЕНЕНИЕ 1: Предзагрузка моделей во время билда ---
# Создаем папки для кэша Hugging Face и InsightFace
RUN mkdir -p /root/.cache/huggingface/hub \
             /root/.insightface/models

# Предзагрузка модели insightface (buffalo_l)
# Используем curl -L для следования редиректам
# Сохраняем в папку, где insightface их ищет
RUN echo "Downloading insightface buffalo_l model..." && \
    curl -L https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip -o /root/.insightface/models/buffalo_l.zip && \
    echo "Extracting insightface buffalo_l model..." && \
    unzip /root/.insightface/models/buffalo_l.zip -d /root/.insightface/models && \
    rm /root/.insightface/models/buffalo_l.zip # Удаляем zip-архив после распаковки

# Предзагрузка моделей ControlNet и Photomaker (их базовые модели) через hf_hub_download
# Это заполнит кэш Hugging Face
ENV HF_HOME /root/.cache/huggingface # Убедимся, что Hugging Face использует эту папку
RUN echo "Downloading ControlNet and PhotoMaker base models via dummy script..." && \
    python3 -c "from huggingface_hub import hf_hub_download; \
                hf_hub_download(repo_id='lllyasviel/ControlNet', filename='ControlNet-v1-1-openpose.pth', cache_dir='/root/.cache/huggingface/hub'); \
                hf_hub_download(repo_id='thibaud/controlnet-openpose-sdxl-1.0', filename='pytorch_model.bin', cache_dir='/root/.cache/huggingface/hub'); \
                hf_hub_download(repo_id='SG161222/RealVisXL_V4.0', filename='pytorch_model.bin', cache_dir='/root/.cache/huggingface/hub'); \
                hf_hub_download(repo_id='TencentARC/PhotoMaker-V2', filename='photomaker-v2.bin', repo_type='model', cache_dir='/root/.cache/huggingface/hub')"
# ---------------------------------------------------------------------------------


# Copy PhotoMaker repo
RUN git clone https://github.com/TencentARC/PhotoMaker.git PhotoMaker-repo

# Copy requirements.txt AFTER cloning PhotoMaker
COPY requirements.txt .

# --- Ключевое изменение 2: Установка Python-зависимостей ---
ARG CACHE_BUSTER=1 
# Устанавливаем все зависимости, включая PhotoMaker из локальной папки
# Используем --index-url для PyTorch с CUDA 11.8.
RUN pip install --no-cache-dir -r requirements.txt \
    ./PhotoMaker-repo \
    --index-url https://download.pytorch.org/whl/cu118 \
    opencv-python-headless
# -------------------------------------------------------------------------

# Copy application code into image (app/, main.py, etc.)
COPY . .

# Debug: list files in /app (optional)
RUN echo "FILES IN /app:" && ls -R /app

# Make the start script executable
RUN chmod +x start.sh

# Default command
CMD ["./start.sh"]