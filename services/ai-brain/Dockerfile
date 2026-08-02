FROM python:3.11-slim

WORKDIR /app

# 1. Install system deps (git for REPO-CLONE, curl and unzip for rclone install)
RUN apt-get update && apt-get install -y --no-install-recommends git curl unzip && \
    curl https://rclone.org/install.sh | bash && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# 2. Copy requirements first for caching
COPY requirements.txt .

# 3. Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy source code last
COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]