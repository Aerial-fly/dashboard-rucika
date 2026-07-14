# Menggunakan OS Linux super ringan yang sudah ada Python 3.9
FROM python:3.9-slim

# Menyiapkan folder kerja di dalam container
WORKDIR /app

# Meng-copy file kebutuhan library
COPY requirements.txt requirements.txt

# Menginstal library Flask & MySQL
RUN pip install --no-cache-dir -r requirements.txt

# Meng-copy seluruh kode backend ke dalam container
COPY . .

# Perintah untuk menjalankan server API
CMD ["python", "app.py"]