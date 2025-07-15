# Используем официальный образ Python.
FROM python:3.10-slim-bullseye
WORKDIR /app

# --- Шаг 1: Установка комплексных системных зависимостей ---
# apt-get update: Обновление списка пакетов.
# apt-get install -y --no-install-recommends: У ошибка `subprocess-exited-with-error` и особенно упорное предупреждение `git was not found` означают, что `python:3.10-slim-bullseye` и наша попытка установить `build-essential` и другие системные библиотеки всё ещё **недостаточны** или **неправильно работают** для сборки всех сложных Python-пакетов, особенно `insightface` и `onnxruntime-gpu`, а также для корректной установки PhotoMaker.



#### 1. `requirements.txt` (Оставляем как есть!)

# Используем официальный образ PyTorch с Python 3.10, CUDA 11.8 и Cuстановка пакетов без рекомендуемых (для уменьшения образа).
#   build-essential: Компиляторы C/C++ (gcc, g++, make), необходимые для сборки многих Python-пакетов.
#   git: Нужен для клонирования репозиториев (например, PhotoMaker).
#   python3-dev: Заголовочные файлы для Python, критически важны для компиляции расширений C/C++.
#   libgl1-mesa-glx, libgomp1, libsm6, libxext6, libxrender1: Часто требуются графическими библиотеками (Pillow, torchvision).
#   ffmpeg: Часто используется для обработки видео/аудио, может быть неявной зависимостью.
# rm -rf /var/lib/apt/lists/*: Очистка кэша APT для уменьшения размера образа.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    git \
    python3-dev \
    libgl1-mesa-glx \
    libgomp1 \
    libsm6 \
    libxext6 \
    libxrender1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# --- Шаг 2: Копирование requirements.txt и клонирование PhotoMaker ---
# Клонируем PhotoMaker перед основной установкой pip, чтобы избежать проблем с git в pip subprocess
RUN git clone https://github.com/TencentARC/PhotoMaker.git PhotoMaker-repo

COPY requirements.txt .

# --- Шаг 3: Установка Python-зависимостей ---
# Эта строка заставит Docker всегда выполнять RUN ниже заново, чтобы избежать проблем с кэшем
ARG CACHE_BUSTER=1 
# Устанавливаем все зависимости из requirements.txt
# Затем устанавливаем PhotoMaker из локально склонированного репозитория (как отдельный пакет)
# Используем --index-url для PyTorch с CUDA 11.8 (это важно для GPU на RunPod)
RUN pip install --no-cache-dir -r requirements.txt \
    ./PhotoMaker-repo \
    --index-url https://download.pytorch.org/whl/cu118

# --- Шаг 4: Копирование остального кода проекта ---
# Копируем ВЕСЬ проект (включая папку app/, model_loader.py, main.py и т.д.) в контейнер.
COPY . .

# --- Шаг 5: Настройка прав и команды запуска ---
RUN chmod +x ./start.sh

CMD ["./start.sh"]