FROM python:3.11-slim

WORKDIR /app

# 1. Copy requirements first for caching
COPY requirements.txt .

# 2. Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 3. Copy source code last
COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]