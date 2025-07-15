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

# Install huggingface_hub explicitly
RUN pip install --no-cache-dir huggingface_hub

# --- Ключевое изменение: УДАЛЯЕМ проблемную строку 404 ---
# Создаем папки для кэша Hugging Face и InsightFace
RUN mkdir -p /root/.cache/huggingface/hub \
             /root/.insightface/models

# Предзагрузка модели insightface (buffalo_l)
RUN echo "Downloading insightface buffalo_l model..." && \
    curl -L https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip -o /root/.insightface/models/buffalo_l.zip && \
    echo "Extracting insightface buffalo_l model..." && \
    unzip /root/.insightface/models/buffalo_l.zip -d /root/.insightface/models && \
    rm /root/.insightface/models/buffalo_l.zip

# Загружаем ОСТАЛЬНЫЕ модели Hugging Face по отдельности, которые точно существуют
ENV HF_HOME /root/.cache/huggingface 
RUN python3 -c "from huggingface_hub import hf_hub_download; print('Downloading controlnet-openpose-sdxl-1.0 pytorch_model.bin'); hf_hub_download(repo_id='thibaud/controlnet-openpose-sdxl-1.0', filename='pytorch_model.bin', cache_dir='/root/.cache/huggingface/hub')"
RUN python3 -c "from huggingface_hub import hf_hub_download; print('Downloading RealVisXL_V4.0 pytorch_model.bin'); hf_hub_download(repo_id='SG161222/RealVisXL_V4.0', filename='pytorch_model.bin', cache_dir='/root/.cache/huggingface/hub')"
RUN python3 -c "from huggingface_hub import hf_hub_download; print('Downloading photomaker-v2.bin'); hf_hub_download(repo_id='TencentARC/PhotoMaker-V2', filename='photomaker-v2.bin', repo_type='model', cache_dir='/root/.cache/huggingface/hub')"
# ------------------------------------------------------------------------------------------------------------------------

# Copy PhotoMaker repo
RUN git clone https://github.com/TencentARC/PhotoMaker.git PhotoMaker-repo

# Copy requirements.txt AFTER cloning PhotoMaker
COPY requirements.txt .

# --- Установка остальных Python-зависимостей ---
ARG CACHE_BUSTER=1 
# Добавляем controlnet_aux[full] для установки всех зависимостей OpenposeDetector
RUN pip install --no-cache-dir -r requirements.txt \
    ./PhotoMaker-repo \
    --index-url https://download.pytorch.org/whl/cu118 \
    opencv-python-headless \
    controlnet_aux[full] # <-- КЛЮЧЕВОЕ ДОБАВЛЕНИЕ

# Copy application code into image
COPY . .

# Debug: list files in /app (optional)
RUN echo "FILES IN /app:" && ls -R /app

# Make the start script executable
RUN chmod +x start.sh

# Default command
CMD ["./start.sh"]