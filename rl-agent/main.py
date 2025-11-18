import os
import json
import numpy as np
import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient, Point
from bandit import Bandit


# =======================
#  Konfiguracja MQTT
# =======================
broker = os.getenv("MQTT_BROKER", "mosquitto")
topic_in = os.getenv("MQTT_TOPIC_IN", "traffic/data")
topic_reward = os.getenv("MQTT_TOPIC_REWARD", "traffic/feedback")
topic_out = os.getenv("MQTT_TOPIC_OUT", "traffic/control")


# =======================
#  Konfiguracja InfluxDB
# =======================
influx_host = os.getenv("INFLUXDB_HOST", "influxdb3-core")
influx_port = os.getenv("INFLUXDB_HTTP_PORT", "8181")
influx_token = os.getenv("INFLUXDB_TOKEN", "")
influx_org = os.getenv("INFLUXDB_ORG", "local_org")
influx_bucket = os.getenv("INFLUXDB_BUCKET", "local_system")

influx_url = f"http://{influx_host}:{influx_port}"
print(f"[INFO] Connecting to InfluxDB at {influx_url}")

influx = InfluxDBClient(
    url=str(influx_url),
    token=str(influx_token),
    org=str(influx_org)
)
write_api = influx.write_api()


# =======================
#  Inicjalizacja modelu RL
# =======================
bandit = Bandit()


# =======================
#  Funkcje pomocnicze
# =======================
def save_to_influx(measurement: str, data: dict):
    """Zapis danych do InfluxDB (bez przerywania pracy w razie błędu)."""
    try:
        point = Point(measurement)
        for k, v in data.items():
            point = point.field(k, float(v))
        write_api.write(bucket=influx_bucket, record=point)
    except Exception as e:
        print(f"[InfluxDB] Write error: {e}")


# =======================
#  Callbacki MQTT
# =======================
def on_data(client, userdata, msg):
    try:
        d = json.loads(msg.payload.decode())
        qA = float(d.get("qA", 0))
        qB = float(d.get("qB", 0))
        peak = float(d.get("peak", 0))

        # wektor kontekstu dla bandyty
        x = np.array([1, qA - qB, abs(qA - qB), qA + qB, peak], dtype=float)
        action = bandit.pick_action(x)

        payload = json.dumps({"preset": int(action)})
        client.publish(topic_out, payload)
        print(f"[MQTT] Sent decision: {payload}")

        save_to_influx("decision", {"qA": qA, "qB": qB, "action": action})
    except Exception as e:
        print(f"[on_data] Error: {e}")


def on_reward(client, userdata, msg):
    try:
        d = json.loads(msg.payload.decode())
        reward = float(d.get("reward", 0))
        a, x = bandit.last_action, bandit.last_context
        if a is not None and x is not None:
            bandit.update(a, x, reward)
            print(f"[RL] Updated: action={a}, reward={reward}")
            save_to_influx("reward", {"action": a, "reward": reward})
    except Exception as e:
        print(f"[on_reward] Error: {e}")


# =======================
#  Główna pętla
# =======================
def main():
    print("[INFO] Starting RL-agent")
    print(f"[INFO] Connecting to MQTT broker '{broker}' ...")

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.message_callback_add(topic_in, on_data)
    client.message_callback_add(topic_reward, on_reward)

    try:
        client.connect(broker, 1883, 60)
        client.subscribe([(topic_in, 0), (topic_reward, 0)])
        print(f"[INFO] Subscribed to: {topic_in}, {topic_reward}")
        client.loop_forever()
    except Exception as e:
        print(f"[ERROR] MQTT connection failed: {e}")


if __name__ == "__main__":
    main()
