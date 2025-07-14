FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
ARG CACHE_BUSTER=1 
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x ./start.sh

CMD ["./start.sh"]