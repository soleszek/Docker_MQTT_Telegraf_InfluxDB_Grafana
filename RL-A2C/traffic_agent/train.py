import os

from stable_baselines3 import A2C

from .env import TrafficLightEnv


def main():
    broker_ip = os.getenv("BROKER_IP", "mosquitto")
    broker_port = int(os.getenv("BROKER_PORT", "1883"))
    model_path = os.getenv("MODEL_PATH", "/app/models/a2c_traffic")
    train_timesteps = int(os.getenv("TRAIN_TIMESTEPS", "50000"))

    print("==== RL TRAFFIC TRAINING (A2C) ====")
    print(f"Broker MQTT: {broker_ip}:{broker_port}")
    print(f"Model target path: {model_path}.zip")
    print(f"Total timesteps: {train_timesteps}")

    env = TrafficLightEnv(
        broker_ip=broker_ip,
        broker_port=broker_port,
    )

    try:
        model = A2C(
            "MultiInputPolicy",
            env,
            verbose=1,
        )

        model.learn(total_timesteps=train_timesteps)

        print(f"Saving model to: {model_path}.zip")
        model.save(model_path)
        print("Training finished.")
    finally:
        env.close()


if __name__ == "__main__":
    main()