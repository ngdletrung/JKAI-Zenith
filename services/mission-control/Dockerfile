# 🧬 JKAI ZENITH: HYBRID MISSION CONTROL v2.0
FROM python:3.10-slim

# 🛠️ Cài đặt Node.js và các công cụ cần thiết cho cả Python & Node
RUN apt-get update && apt-get install -y \
    curl \
    libpq-dev \
    procps \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 🐍 Setup Backend
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r ./backend/requirements.txt
RUN pip install psutil psycopg2-binary gunicorn gevent gevent-websocket

# 🎨 Setup Frontend (Dùng cho Live Dev)
COPY frontend/package*.json ./frontend/
RUN cd frontend && npm install --legacy-peer-deps --force

# Copy toàn bộ code
COPY . .

EXPOSE 9999
EXPOSE 9998

# 🚀 Script khởi động kép
RUN echo '#!/bin/sh\n\
    cd /app/frontend && npm run dev -- --host 0.0.0.0 --port 9999 &\n\
    cd /app/backend && gunicorn -k geventwebsocket.gunicorn.workers.GeventWebSocketWorker -w 1 --bind 0.0.0.0:9998 main:app\n\
    ' > /app/start.sh && chmod +x /app/start.sh

CMD ["/app/start.sh"]