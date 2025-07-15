FROM python:3.10-slim-bullseye 

WORKDIR /app

# --- Ключевое изменение: Устанавливаем git ПЕРЕД установкой зависимостей Python ---
# git нужен для установки git+https://... зависимостей
RUN apt-get update && apt-get install -y git \
    && rm -rf /var/lib/apt/lists/* # Очистка кэша apt
# ---------------------------------------------------------------------------------

# Копируем файл с зависимостями в контейнер.
COPY requirements.txt .

# Эта строка заставит Docker всегда выполнять RUN ниже заново, чтобы избежать проблем с кэшем
ARG CACHE_BUSTER=1 
# Устанавливаем обновленные зависимости.
# --- Ключевое изменение: Используем --index-url для PyTorch с CUDA 11.8 ---
RUN pip install --no-cache-dir -r requirements.txt \
    --index-url https://download.pytorch.org/whl/cu118 # <-- Эта строка для PyTorch CUDA
# -------------------------------------------------------------------------

# Копируем ВЕСЬ проект (включая папку app/, model_loader.py, main.py и т.д.) в контейнер.
COPY . .

# Даем нашему скрипту права на выполнение.
RUN chmod +x ./start.sh

# Команда, которая будет выполняться при запуске контейнера.
CMD ["./start.sh"]