FROM python:3.10-slim

# Устанавливаем рабочую директорию внутри контейнера.
WORKDIR /app

# Копируем файл с зависимостями в контейнер.
COPY requirements.txt .
ARG CACHE_BUSTER=1

# Устанавливаем обновленные зависимости.
RUN pip install --no-cache-dir -r requirements.txt

# Копируем все файлы проекта в контейнер.
COPY . .

# Даем нашему скрипту права на выполнение.
RUN chmod +x ./start.sh

# Команда, которая будет выполняться при запуске контейнера.
CMD ["./start.sh"]