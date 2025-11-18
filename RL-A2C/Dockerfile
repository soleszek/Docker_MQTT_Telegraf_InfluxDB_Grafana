FROM python:3.10-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV PYTHONUNBUFFERED=1

COPY requirements.txt .

RUN python -m pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . /app

# Domyślnie tryb inference
ENV RL_MODE=infer

# Przełącznik trybu na podstawie RL_MODE
CMD ["sh", "-c", "if [ \"$RL_MODE\" = \"train\" ]; then python -m traffic_agent.train; else python -m traffic_agent.inference; fi"]