# Bazowy obraz – taki sam jak w YOLO
FROM python:3.12-slim

# Ustaw katalog roboczy
WORKDIR /app

# Skopiuj skrypt serwera Flask
COPY upload_server.py .

# Zainstaluj Flask
RUN pip install --no-cache-dir flask

# Utwórz katalog na pliki (po stronie kontenera)
RUN mkdir -p /app/uploads

# Otwórz port 5000
EXPOSE 5000

# Uruchom serwer
CMD ["python", "upload_server.py"]