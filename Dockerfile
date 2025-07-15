FROM pytorch/pytorch:2.3.0-cuda11.8-cudnn8-runtime

WORKDIR /app

# Устанавливаем системные зависимости, которые могут отсутствовать в PyTorch образе, но часто нужны.
# git нужен для клонирования репозиториев (если PhotoMaker снова потребует git-установки или для других зависимостей).
# ffmpeg часто используется для обработки медиа.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Обновляем pip и устанавливаем необходимые инструменты для сборки (на всякий случай)
RUN pip install --upgrade pip setuptools wheel

# Копируем PhotoMaker репозиторий, так как pip install photomaker может быть недостаточно
# или PyPI версия не та, что нужна.
RUN git clone https://github.com/TencentARC/PhotoMaker.git PhotoMaker-repo

COPY requirements.txt .

ARG CACHE_BUSTER=1
# Устанавливаем все остальные Python зависимости.
# PyTorch и torchvision уже установлены базовым образом, так что их строки из requirements.txt
# просто будут проигнорированы pip.
# PhotoMaker устанавливаем из локально склонированного репозитория.
# --index-url для PyTorch WHL теперь НЕ НУЖЕН, т.к. PyTorch уже есть.
RUN pip install --no-cache-dir -r requirements.txt ./PhotoMaker-repo

COPY . .

RUN chmod +x ./start.sh

CMD ["./start.sh"]