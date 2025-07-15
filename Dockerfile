# Используем официальный образ Python с поддержкой CUDA, если возможно, или slim
# Но лучше использовать slim, а CUDA-зависимости ставить через pip, как в requirements.txt
FROM python:3.10-slim-bullseye 

WORKDIR /app

# Установка git - нужен для клонирования PhotoMaker из GitHub
RUN apt-get update && apt-get install -y git \
    && rm -rf /var/lib/apt/lists/* # Очистка кэша apt

# Копируем файл с зависимостями в контейнер.
COPY requirements.txt .

# Эта строка заставит Docker всегда выполнять RUN ниже заново
ARG CACHE_BUSTER=1 
# Устанавливаем обновленные зависимости.
RUN pip install --no-cache-dir -r requirements.txt

# Копируем ВЕСЬ проект (включая папку app/, model_loader.py, main.py и т.д.) в контейнер.
COPY . .

# Даем нашему скрипту права на выполнение.
RUN chmod +x ./start.sh

# Команда, которая будет выполняться при запуске контейнера.
CMD ["./start.sh"]