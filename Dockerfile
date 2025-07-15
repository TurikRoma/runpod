FROM pytorch/pytorch:2.3.0-cuda11.8-cudnn8-runtime

WORKDIR /app

# --- Шаг 1: Установка дополнительных системных зависимостей ---
# git: Нужен для клонирования репозиториев.
# ffmpeg: Часто используется для обработки медиа.
# cmake, libprotobuf-dev: Часто требуются для сборки ONNX-related библиотек (onnxruntime-gpu, insightface)
# libsm6, libxext6, libxrender1: Часто нужны для различных графических и видео-библиотек.
# libgl1-mesa-glx: Для OpenGL, часто требуется Pillow, torchvision.
# python3-dev: Заголовочные файлы для Python, важны для компиляции расширений.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git \
    ffmpeg \
    cmake \
    libprotobuf-dev \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgl1-mesa-glx \
    python3-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Обновляем pip и устанавливаем необходимые инструменты для сборки (важно для сложных пакетов)
# Запускаем в отдельном RUN, чтобы избежать кэширования и убедиться, что они актуальны
RUN pip install --upgrade pip setuptools wheel

# --- Шаг 2: Клонируем PhotoMaker репозиторий ---
RUN git clone https://github.com/TencentARC/PhotoMaker.git PhotoMaker-repo

# --- Шаг 3: Установка зависимостей Python (в несколько этапов для надежности) ---
# Эта строка заставит Docker всегда выполнять RUN ниже заново, чтобы избежать проблем с кэшем
ARG CACHE_BUSTER=1 

# Устанавливаем критические пакеты, которые часто вызывают проблемы, отдельно
# insightface часто зависит от specific onnxruntime versions
# Установка opencv-python-headless для избежания проблем с графическими зависимостями OpenCV
RUN pip install --no-cache-dir \
    onnxruntime-gpu \
    insightface==0.7.3 \
    opencv-python-headless # Установка headless версии, чтобы избежать зависимостей UI

# Устанавливаем остальные зависимости из requirements.txt
# PyTorch и torchvision уже установлены базовым образом, так что их строки просто будут проигнорированы.
# PhotoMaker устанавливаем из локально склонированного репозитория.
COPY requirements.txt . 

RUN pip install --no-cache-dir -r requirements.txt ./PhotoMaker-repo

# --- Шаг 4: Копирование остального кода проекта ---
COPY . .

# --- Шаг 5: Настройка прав и команды запуска ---
RUN chmod +x ./start.sh

CMD ["./start.sh"]