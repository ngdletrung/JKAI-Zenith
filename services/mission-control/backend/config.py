import os

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'JKAI-ZENITH-SUPER-SECRET-KEY-999')
    REDIS_URL = os.getenv('REDIS_URL', 'redis://redis-ai:6379/0')
    
    # AI Service URLs - Tất cả dùng port 8000 nội bộ trong Docker Network
    AI_BRAIN_URL = os.getenv('AI_BRAIN_URL', 'http://ai-brain:8000')
    EXECUTOR_URL = os.getenv('EXECUTOR_URL', 'http://ai-executor-1:8000')
    BROWSER_URL = os.getenv('BROWSER_SERVICE_URL', 'http://ai-browser:8000')
    AI_CONTROL_PLANE_URL = os.getenv('AI_CONTROL_PLANE_URL', 'http://ai-control-plane:8000')
    OLLAMA_HOST = os.getenv('OLLAMA_HOST', 'http://host.docker.internal:11434')
    QDRANT_URL = os.getenv('QDRANT_URL', 'http://qdrant:6333')
    
    # DB URLs
    POSTGRES_USER = os.getenv('POSTGRES_USER', 'n8n')
    POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', '')
    POSTGRES_DB = os.getenv('POSTGRES_DB', 'n8n')
    POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'postgres')
    POSTGRES_URL = os.getenv('POSTGRES_URL', f'postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:5432/{POSTGRES_DB}')
    
    # Log Retention
    MAX_HISTORY_LOGS = 500

config = Config()

