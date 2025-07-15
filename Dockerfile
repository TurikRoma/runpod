FROM python:3.10-slim
WORKDIR /app

# ---- до pip install: устанавливаем git и инструменты сборки ----
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      build-essential git python3-dev libffi-dev \
      ffmpeg libgl1 libglib2.0-0 libsm6 libxrender1 libxext6 && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir "pip<24.1"
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chmod +x ./start.sh
CMD ["./start.sh"]