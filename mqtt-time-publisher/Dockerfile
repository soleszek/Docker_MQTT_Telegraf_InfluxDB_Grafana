FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir paho-mqtt

COPY time_publisher.py .

CMD ["python", "time_publisher.py"]