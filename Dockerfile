FROM python:3.10-slim-bullseye 

WORKDIR /app

# --- Шаг 1: Установка системных зависимостей ---
# apt-get update: Обновление списка пакетов
# apt-get install -y --no-install-recommends: Установка пакетов без рекомендуемых (для уменьшения образа)
#   build-essential: Компиляторы C/C++ (gcc, g++, make), необходимые для сборки многих Python-пакетов.
#   git: Нужен для клонирования репозиториев (например, PhotoMaker).
#   libgl1-mesa-glx: Зависимость, часто требуемая графическими библиотеками (например, Pillow, torchvision)
#                    для работы с изображениями, даже на CPU.
#   libgomp1: OpenMP runtime library, часто зависимость для оптимизированных численных библиотек (например, torch).
#   libsm6, libxext6, libxrender1: Часто нужны для различных графических и видео-библиотек.
# rm -rf /var/lib/apt/lists/*: Очистка кэша APT для уменьшения размера образа.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    git \
    libgl1-mesa-glx \
    libgomp1 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# --- Шаг 2: Копирование requirements.txt и клонирование PhotoMaker ---
COPY requirements.txt .

# Клонируем PhotoMaker перед установкой pip, чтобы избежать проблем с git в pip subprocess
RUN git clone https://github.com/TencentARC/PhotoMaker.git PhotoMaker-repo

# --- Шаг 3: Установка Python-зависимостей ---
# Эта строка заставит Docker всегда выполнять RUN ниже заново, чтобы избежать проблем с кэшем
ARG CACHE_BUSTER=1 
# Устанавливаем все зависимости из requirements.txt
# Затем устанавливаем PhotoMaker из локально склонированного репозитория
# Используем --index-url для PyTorch с CUDA 11.8
RUN pip install --no-cache-dir -r requirements.txt \
    ./PhotoMaker-repo \
    --index-url https://download.pytorch.org/whl/cu118

# --- Шаг 4: Копирование остального кода проекта ---
COPY . .

# --- Шаг 5: Настройка прав и команды запуска ---
RUN chmod +x ./start.sh

CMD ["./start.sh"]