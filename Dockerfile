FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system packages for C-extension builds, Git, Curl, image/video libs
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      build-essential git python3-dev libffi-dev curl \
      ffmpeg libgl1 libglib2.0-0 libsm6 libxrender1 libxext6 && \
    rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
# Pin pip to <24.1 to allow legacy metadata
RUN pip install --no-cache-dir "pip<24.1"
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code into image
COPY . .

# Debug: list files in /app (optional)
RUN echo "FILES IN /app:" && ls -R /app

# Make the start script executable
RUN chmod +x start.sh

# Default command
CMD ["./start.sh"]