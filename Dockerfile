# Gunakan Python slim official image
FROM python:3.11-slim

# Set working directory di container
WORKDIR /app

# Copy requirements.txt dulu untuk caching layer lebih efisien
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy semua source code ke container
COPY . .

# Set environment variable PORT (Fly.io gunakan port ini)
ENV PORT=8080

# Jalankan aplikasi
CMD ["python", "app.py"]
