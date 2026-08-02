FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY api/        ./api/
COPY core/       ./core/
COPY static/     ./static/
COPY templates/  ./templates/
COPY config.py   .
COPY main.py     .
CMD ["python", "main.py"]