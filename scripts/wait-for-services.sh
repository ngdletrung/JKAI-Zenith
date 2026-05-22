#!/usr/bin/env bash
set -euo pipefail

echo "=========================================="
echo "  WAIT FOR SERVICES SCRIPT v2.0"
echo "=========================================="

# Màu sắc cho output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Hàm log
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 1. Kiểm tra Postgres
DB_HOST="${DB_POSTGRESDB_HOST:-postgres}"
DB_PORT="${DB_POSTGRESDB_PORT:-5432}"
DB_USER="${DB_POSTGRESDB_USER:-n8n}"
DB_NAME="${DB_POSTGRESDB_DATABASE:-n8n}"

log_info "Đang đợi Postgres tại ${DB_HOST}:${DB_PORT}..."

MAX_RETRIES=30
RETRY_COUNT=0

while ! nc -z "$DB_HOST" "$DB_PORT" 2>/dev/null; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
        log_error "Postgres không khả dụng sau $MAX_RETRIES lần thử"
        exit 1
    fi
    log_warn "Postgres chưa sẵn sàng, thử lại sau 2 giây ($RETRY_COUNT/$MAX_RETRIES)"
    sleep 2
done

log_info "✅ Postgres đã sẵn sàng!"

# 2. Kiểm tra Redis
REDIS_HOST="${QUEUE_BULL_REDIS_HOST:-redis}"
REDIS_PORT="${QUEUE_BULL_REDIS_PORT:-6379}"

log_info "Đang đợi Redis tại ${REDIS_HOST}:${REDIS_PORT}..."

RETRY_COUNT=0
while ! nc -z "$REDIS_HOST" "$REDIS_PORT" 2>/dev/null; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
        log_error "Redis không khả dụng sau $MAX_RETRIES lần thử"
        exit 1
    fi
    log_warn "Redis chưa sẵn sàng, thử lại sau 2 giây ($RETRY_COUNT/$MAX_RETRIES)"
    sleep 2
done

log_info "✅ Redis đã sẵn sàng!"

# 3. Kiểm tra Ollama (optional)
if [ -n "${OLLAMA_HOST:-}" ]; then
    log_info "Kiểm tra kết nối Ollama tại ${OLLAMA_HOST}..."
    
    RETRY_COUNT=0
    while ! curl -s "${OLLAMA_HOST}" > /dev/null 2>&1; do
        RETRY_COUNT=$((RETRY_COUNT + 1))
        if [ $RETRY_COUNT -ge 10 ]; then
            log_warn "Ollama không khả dụng, tiếp tục khởi động (AI Brain sẽ xử lý sau)"
            break
        fi
        log_warn "Ollama chưa sẵn sàng, thử lại sau 3 giây ($RETRY_COUNT/10)"
        sleep 3
    done
    
    if curl -s "${OLLAMA_HOST}" > /dev/null 2>&1; then
        log_info "✅ Ollama đã sẵn sàng!"
    fi
fi

# 4. Xác định role và khởi động
ROLE="${1:-n8n}"
log_info "Khởi động với role: ${ROLE}"

if [ "$ROLE" = "worker" ]; then
    log_info "🚀 Khởi động n8n worker mode..."
    exec n8n worker
elif [ "$ROLE" = "webhook" ]; then
    log_info "🚀 Khởi động n8n webhook mode..."
    exec n8n webhook
else
    log_info "🚀 Khởi động n8n main mode..."
    exec n8n start
fi