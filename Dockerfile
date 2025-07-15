FROM python:3.10-slim

WORKDIR /app

# 1) Системные библиотеки и инструменты для сборки C-расширений
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      build-essential git python3-dev libffi-dev \
      ffmpeg libgl1 libglib2.0-0 libsm6 libxrender1 libxext6 && \
    rm -rf /var/lib/apt/lists/*

# 2) Копируем и ставим Python-зависимости
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# 3) Копируем весь код
COPY . .

# 4) Делаем скрипт запуска executable
RUN chmod +x ./start.sh

# 5) Точка входа
CMD ["./start.sh"]