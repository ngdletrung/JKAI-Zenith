FROM python:3.11-slim

RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create temp dir for audio processing
RUN mkdir -p /tmp/audio

COPY bot.py .

CMD ["python", "bot.py"]
