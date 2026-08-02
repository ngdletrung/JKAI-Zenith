#!/bin/sh
set -e

echo "ðŸš€ [JKAI] Starting Mission Control backend (9998)..."
cd /app/backend
gunicorn -k geventwebsocket.gunicorn.workers.GeventWebSocketWorker -w 1 --bind 0.0.0.0:9998 main:app &
BACKEND_PID=$!

echo "â³ [JKAI] Waiting for backend Socket.IO..."
TRIES=0
until curl -sf "http://127.0.0.1:9998/api/ping" >/dev/null 2>&1; do
  TRIES=$((TRIES + 1))
  if [ "$TRIES" -ge 90 ]; then
    echo "âŒ [JKAI] Backend did not become ready in time."
    exit 1
  fi
  sleep 1
done
echo "âœ… [JKAI] Backend ready."

echo "ðŸŽ¨ [JKAI] Starting Vite frontend (9999)..."
cd /app/frontend
npm run dev -- --host 0.0.0.0 --port 9999 &
FRONTEND_PID=$!

wait "$BACKEND_PID" "$FRONTEND_PID"
