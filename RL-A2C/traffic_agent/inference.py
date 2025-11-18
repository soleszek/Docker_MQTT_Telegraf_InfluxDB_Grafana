import os
import time
from pathlib import Path

from stable_baselines3 import A2C

from .env import TrafficLightEnv


def find_model_path(base_path: str) -> Path | None:
    """
    Szuka pliku modelu.
    Jeśli base_path ma rozszerzenie .zip -> sprawdzamy dokładnie ten plik.
    W przeciwnym razie sprawdzamy base_path + '.zip'.
    """
    p = Path(base_path)
    candidates = []
    if p.suffix == ".zip":
        candidates.append(p)
    else:
        candidates.append(p.with_suffix(".zip"))

    for c in candidates:
        if c.is_file():
            return c
    return None


def main():
    broker_ip = os.getenv("BROKER_IP", "mosquitto")
    broker_port = int(os.getenv("BROKER_PORT", "1883"))
    raw_model_path = os.getenv("MODEL_PATH", "/app/models/a2c_traffic")
    step_delay = float(os.getenv("STEP_DELAY", "2.0"))

    print("==== RL TRAFFIC AGENT (A2C Inference) ====")
    print(f"Broker MQTT: {broker_ip}:{broker_port}")
    print(f"MODEL_PATH env: {raw_model_path}")
    print(f"STEP_DELAY: {step_delay}s")

    model_file = find_model_path(raw_model_path)
    if model_file is None:
        print("NO MODEL FOUND.")
        print("Expected model file at:")
        print(f" - {raw_model_path} or {raw_model_path}.zip")
        print("Train the model first (RL_MODE=train) so that a2c_traffic.zip is created.")
        return

    print(f"Loading model from: {model_file}")
    # A2C.load spodziewa się ścieżki bez .zip, więc bierzemy stem
    model_load_path = str(model_file.with_suffix(""))
    model = A2C.load(model_load_path)

    env = TrafficLightEnv(
        broker_ip=broker_ip,
        broker_port=broker_port,
    )

    try:
        obs, _ = env.reset()
        while True:
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, info = env.step(action)
            env.render()
            if step_delay > 0:
                time.sleep(step_delay)
            if terminated or truncated:
                obs, _ = env.reset()
    finally:
        env.close()


if __name__ == "__main__":
    main()