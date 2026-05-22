# ===== Base: Node + Debian Bullseye (Slim) =====
FROM node:20-bullseye-slim

# ── Biến môi trường ───────────────────────────────────
ENV DEBIAN_FRONTEND=noninteractive \
    TZ=Asia/Bangkok \
    PYTHONUNBUFFERED=1 \
    NODE_FUNCTION_ALLOW_BUILTIN=child_process,fs,path,os \
    NODE_FUNCTION_ALLOW_EXTERNAL=axios,moment,lodash,redis

# ===== System packages =====
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip \
    ffmpeg libsndfile1 git curl ca-certificates \
    jq netcat-openbsd tini \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# ===== Python Core Libraries =====
RUN pip3 install --no-cache-dir \
    requests \
    python-dotenv \
    redis \
    qdrant-client \
    numpy \
    pandas \
    openai \
    pydantic \
    uvicorn \
    fastapi

# ===== Thư mục làm việc =====
WORKDIR /usr/src/app
RUN mkdir -p /scripts /files /root/.n8n /data/obsidian

# ===== Cài đặt n8n version ổn định =====
ARG N8N_VERSION
ENV N8N_VERSION=${N8N_VERSION}
RUN npm config set fetch-retry-maxtimeout 600000 && \
    npm config set fetch-retries 10 && \
    npm install -g n8n@${N8N_VERSION} --omit=dev

# ===== Copy scripts =====
COPY --chmod=755 ./scripts/wait-for-services.sh /scripts/wait-for-services.sh

# ===== Healthcheck =====
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:5678/healthz || exit 1

# ===== Expose ports =====
EXPOSE 5678

# ===== Entrypoint =====
ENTRYPOINT ["tini", "--", "/scripts/wait-for-services.sh"]

# ===== Default command =====
CMD ["n8n"]