FROM python:3.11-slim

WORKDIR /app

# 1. Install system dependencies first
RUN apt-get update && apt-get install -y ca-certificates && rm -rf /var/lib/apt/lists/*

# 2. Pre-install Playwright and Chromium to CACHE the large download (Macro Optimization)
RUN pip install playwright
RUN playwright install --with-deps chromium

# 3. Copy requirements and install remaining Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy source code last
COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]