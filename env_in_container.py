import os
import time
import logging
import socket
import paho.mqtt.client as mqtt

LOG = logging.getLogger("traffic_agent")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def make_mqtt_client(*args, **kwargs):
    """
    Tworzy klienta mqtt kompatybilnego z paho-mqtt 1.x i 2.x.
    Preferujemy CallbackAPIVersion.V4 (stare callbacki). Jeśli podanie
    callback_api_version podniesie wyjątek, fallbackujemy do tworzenia bez parametru.
    """
    CallbackAPIVersion = getattr(mqtt, "CallbackAPIVersion", None)
    if CallbackAPIVersion is not None:
        api_v4 = getattr(CallbackAPIVersion, "V4", None)
        if api_v4 is not None:
            try:
                return mqtt.Client(*args, callback_api_version=api_v4, **kwargs)
            except (TypeError, ValueError) as e:
                LOG.debug("mqtt.Client rejected callback_api_version V4 (%s), falling back: %s", api_v4, e)
        # fallback: try V5 only if V4 unavailable
        api_v5 = getattr(CallbackAPIVersion, "V5", None)
        if api_v5 is not None:
            try:
                return mqtt.Client(*args, callback_api_version=api_v5, **kwargs)
            except (TypeError, ValueError) as e:
                LOG.debug("mqtt.Client rejected callback_api_version V5 (%s), falling back: %s", api_v5, e)
    # ostateczny fallback: bez parametru (kompatybilne z paho 1.x)
    return mqtt.Client(*args, **kwargs)


class TrafficLightEnv:
    def __init__(self,
                 broker_ip: str | None = None,
                 broker_port: int | None = None,
                 client_id: str = "traffic-agent",
                 connect_retries: int = 20,
                 retry_delay: float = 1.0):
        self.broker = broker_ip or os.getenv("BROKER_IP", "mosquitto")
        self.port = int(broker_port or os.getenv("BROKER_PORT", "1883"))
        self.client_id = client_id

        self._client = make_mqtt_client(client_id)

        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        self._client.on_disconnect = self._on_disconnect

        self._connect_with_retries(retries=connect_retries, delay=retry_delay)
        self._client.loop_start()

    def _connect_with_retries(self, retries: int, delay: float):
        attempt = 0
        while attempt < retries:
            attempt += 1
            try:
                LOG.info("[MQTT] Connecting to broker %s:%s (attempt %d/%d)", self.broker, self.port, attempt, retries)
                self._client.connect(self.broker, self.port, keepalive=60)
                LOG.info("[MQTT] Connected to %s:%s", self.broker, self.port)
                return
            except (socket.gaierror, OSError) as e:
                LOG.warning("[MQTT] Connection failed (attempt %d/%d): %s", attempt, retries, e)
            except Exception as e:
                LOG.exception("[MQTT] Unexpected error while connecting (attempt %d/%d): %s", attempt, retries, e)
            time.sleep(delay)
        raise RuntimeError(f"Could not connect to MQTT broker {self.broker}:{self.port} after {retries} attempts")

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            LOG.info("[MQTT] on_connect: success, rc=%s", rc)
            try:
                client.subscribe("traffic/+/state")
                LOG.info("[MQTT] Subscribed to traffic/+/state")
            except Exception:
                LOG.exception("[MQTT] Failed to subscribe on connect")
        else:
            LOG.warning("[MQTT] on_connect: returned code %s", rc)

    def _on_message(self, client, userdata, msg):
        LOG.debug("[MQTT] Message received on %s: %s", msg.topic, msg.payload)

    def _on_disconnect(self, client, userdata, rc):
        LOG.warning("[MQTT] Disconnected (rc=%s).", rc)

    def publish(self, topic: str, payload: str, qos: int = 0, retain: bool = False):
        try:
            result = self._client.publish(topic, payload, qos=qos, retain=retain)
            LOG.debug("[MQTT] Published to %s: %s (result=%s)", topic, payload, result)
            return result
        except Exception:
            LOG.exception("[MQTT] Failed to publish to %s", topic)
            raise

    def reset(self):
        obs = None
        info = {}
        return obs, info

    def step(self, action):
        obs = None
        reward = 0.0
        done = False
        info = {}
        return obs, reward, done, info

    def render(self):
        pass

    def close(self):
        try:
            self._client.loop_stop()
            self._client.disconnect()
        except Exception:
            LOG.exception("Error while closing MQTT client")