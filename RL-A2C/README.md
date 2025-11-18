# RL Traffic Light Agent — traffic signal control using RL and MQTT

This project enables the training and deployment of a reinforcement learning agent that controls traffic lights managed by Arduino. Communication between the agent (Python) and Arduino is carried out over MQTT.

---

## Project Structure

```
traffic-rl/
├── Dockerfile
├── requirements.txt
├── traffic_agent/
│   ├── __init__.py
│   ├── env.py
│   ├── inference.py
├── train.py
├── models/
│   └── a2c_traffic.zip        # Trained RL model
├── logs/
├── README.md
└── docker-compose.yml
```

---

## Requirements

- Docker
- docker-compose
- (Hardware) Arduino running the required MQTT firmware (see Arduino section)
- MQTT broker (e.g., Mosquitto)

---

## Quick Start

### 1. (Optional) Training the agent

You can change the broker/MQTT parameters in `train.py` or set the environment variables `BROKER_IP`, `BROKER_PORT` before starting.  
Start RL training:
```
docker-compose run --rm traffic-agent python train.py
```
The model will be saved in the `models/` directory.

### 2. Run the traffic light agent

The trained RL model (`a2c_traffic.zip`) should be placed in `./models`.  
Launch the agent (and the broker, if needed):
```
docker-compose up --build
```
By default, the agent communicates with the MQTT broker started as the `mosquitto` service.

---

## Environment variables

- `BROKER_IP` — address (or Docker service name) of the MQTT broker, e.g., `mosquitto`
- `BROKER_PORT` — MQTT port (default: 1883)
- `MODEL_PATH` — path to the RL model
- `STEP_DELAY` — delay in seconds between agent's decisions

---

## Integration with Arduino

Your Arduino code:
- Publishes the current state of each traffic light to the `traffic/status` MQTT topic.
- Receives commands from the RL agent via the `traffic/action` MQTT topic.  
(See the `env.py` source code for message format and more details.)

---

## Customization and notes

- You can extend the Gymnasium environment (`traffic_agent/env.py`) with custom reward strategies, additional sensors, etc.
- The `train.py` and `traffic_agent/inference.py` scripts allow you to train or deploy the agent independently.
- Logs are saved in `logs/`.

---

## Troubleshooting

- If the agent cannot communicate with Arduino via MQTT, check networking, correct topic names, and Docker network settings.
- Library versions are listed in `requirements.txt`.

---

## Contact

Author: [Your Name or Nickname]