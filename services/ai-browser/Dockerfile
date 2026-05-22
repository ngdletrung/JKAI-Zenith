FROM mcr.microsoft.com/playwright/python:v1.49.0-noble

WORKDIR /app

# 1. Nâng cấp pip và cài đặt Playwright core
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir playwright

# 2. Cài đặt các phụ thuộc hệ thống và Chromium (Bước này nặng nhất nên được cache tuyệt đối)
RUN playwright install-deps chromium && \
    playwright install chromium

# 3. Sao chép requirements và cài đặt các thư viện khác
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Thiết lập biến môi trường
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
ENV PYTHONUNBUFFERED=1

# 5. Cuối cùng mới sao chép mã nguồn (thường xuyên thay đổi)
COPY . .

# Mở cổng cho API
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
