import json
import threading
import time
from typing import Dict, Tuple, Any

import gymnasium as gym
from gymnasium import spaces
import numpy as np
import paho.mqtt.client as mqtt


def make_mqtt_client(client_id: str | None = None) -> mqtt.Client:
    """
    Tworzy klienta MQTT kompatybilnego z paho-mqtt 1.x.
    Jeśli kiedyś podmienisz na 2.x, tutaj można dodać callback_api_version.
    """
    return mqtt.Client(client_id=client_id)


class TrafficLightEnv(gym.Env):
    """
    Environment dla sterowania sygnalizacją świetlną.
    Odczyt:
      - MQTT topic: traffic/status (publikowany przez Arduino)
    Zapis:
      - MQTT topic: traffic/action (czytany przez Arduino w kolejnym etapie)

    Observation:
      Dict(
        cars: Box(shape=(4,), int32)   -> liczba aut na każdym sygnalizatorze
        state: Box(shape=(4,), int32)  -> stan sygnalizatora (0=RED,1=GREEN,2=YELLOW,3=RED+YELLOW)
        duration: Box(shape=(4,), int32) -> czas czerwonego w ms (tl["d"])
      )

    Action:
      Discrete(4) -> indeks sygnalizatora, który agent "wybiera" jako aktywny.
    """

    metadata = {"render.modes": ["human"]}

    def __init__(
        self,
        broker_ip: str = "mosquitto",
        broker_port: int = 1883,
        status_topic: str = "traffic/status",
        action_topic: str = "traffic/action",
        num_lights: int = 4,
        max_cars: int = 50,
        max_duration_ms: int = 300000,
        obs_timeout: float = 3.0,
        client_id: str | None = "rl_traffic_env",
    ):
        super().__init__()
        self.broker_ip = broker_ip
        self.broker_port = broker_port
        self.status_topic = status_topic
        self.action_topic = action_topic
        self.num_lights = num_lights
        self.max_cars = max_cars
        self.max_duration_ms = max_duration_ms
        self.obs_timeout = obs_timeout

        # Observation space
        self.observation_space = spaces.Dict(
            {
                "cars": spaces.Box(
                    low=0,
                    high=max_cars,
                    shape=(num_lights,),
                    dtype=np.int32,
                ),
                "state": spaces.Box(
                    low=0,
                    high=3,  # 0..3 jak w Arduino (RED, GREEN, YELLOW, RED+YELLOW)
                    shape=(num_lights,),
                    dtype=np.int32,
                ),
                "duration": spaces.Box(
                    low=0,
                    high=max_duration_ms,
                    shape=(num_lights,),
                    dtype=np.int32,
                ),
            }
        )

        # Action space: wybór sygnalizatora 0..3
        self.action_space = spaces.Discrete(num_lights)

        # Ostatnia obserwacja i mechanika synchronizacji
        self._last_obs: Dict[str, np.ndarray] | None = None
        self._obs_lock = threading.Lock()
        self._obs_event = threading.Event()

        self._step = 0
        self._episode_reward = 0.0

        # MQTT setup
        self._client = make_mqtt_client(client_id)
        self._client.on_message = self._on_message
        self._client.on_connect = self._on_connect

        max_tries = 20
        for attempt in range(max_tries):
            try:
                print(f"[MQTT] Connecting to broker {self.broker_ip}:{self.broker_port} (attempt {attempt+1}/{max_tries})")
                self._client.connect(self.broker_ip, self.broker_port)
                print("[MQTT] Connected to broker")
                break
            except Exception as e:
                print(f"[MQTT] Connection failed (attempt {attempt+1}/{max_tries}): {e}")
                time.sleep(2)
        else:
            raise RuntimeError("Could not connect to MQTT broker after multiple attempts")

        self._client.loop_start()
        self._client.subscribe(self.status_topic)

    # MQTT callbacks

    def _on_connect(self, client: mqtt.Client, userdata, flags, rc):
        if rc == 0:
            print(f"[MQTT] on_connect: success, rc={rc}")
            client.subscribe(self.status_topic)
        else:
            print(f"[MQTT] on_connect: error, rc={rc}")

    def _on_message(self, client: mqtt.Client, userdata, msg):
        try:
            payload = msg.payload.decode("utf-8")
            data = json.loads(payload)
            # Oczekujemy formatu:
            # {
            #   "t": <timestamp>,
            #   "l": [
            #     {"i": idx, "c": cars, "s": state, "w": willTurn, "d": duration}, ...
            #   ]
            # }
            lights = data.get("l", [])
            cars_list = np.zeros(self.num_lights, dtype=np.int32)
            state_list = np.zeros(self.num_lights, dtype=np.int32)
            duration_list = np.zeros(self.num_lights, dtype=np.int32)

            for tl in lights:
                idx = int(tl.get("i", 0))
                if idx < 0 or idx >= self.num_lights:
                    continue
                cars_val = int(tl.get("c", -1))
                # jeśli -1 (brak danych z YOLO), to możemy przyjąć 0 lub zostawić 0
                if cars_val < 0:
                    cars_val = 0
                cars_list[idx] = cars_val

                state_val = int(tl.get("s", 0))
                state_list[idx] = state_val

                duration_val = int(tl.get("d", 0))
                if duration_val < 0:
                    duration_val = 0
                duration_list[idx] = duration_val

            obs = {
                "cars": cars_list,
                "state": state_list,
                "duration": duration_list,
            }

            with self._obs_lock:
                self._last_obs = obs
                self._obs_event.set()
        except Exception as e:
            print("[MQTT] Parsing error in _on_message:", e)

    # Gym API

    def reset(self, *, seed: int | None = None, options: Dict[str, Any] | None = None) -> Tuple[Dict[str, np.ndarray], Dict]:
        super().reset(seed=seed)
        self._step = 0
        self._episode_reward = 0.0
        self._obs_event.clear()
        obs = self._wait_for_obs()
        return obs, {}

    def _wait_for_obs(self) -> Dict[str, np.ndarray]:
        """
        Czeka na nową obserwację do czasu self.obs_timeout.
        """
        self._obs_event.clear()
        waited = 0.0
        sleep_int = 0.1
        while waited < self.obs_timeout:
            with self._obs_lock:
                last_obs = self._last_obs
            if last_obs is not None:
                return last_obs
            time.sleep(sleep_int)
            waited += sleep_int
        raise TimeoutError("[MQTT] Timeout waiting for traffic/status")

    def step(self, action: int) -> Tuple[Dict[str, np.ndarray], float, bool, bool, Dict]:
        if not self.action_space.contains(action):
            raise ValueError(f"Invalid action {action} for Discrete({self.num_lights})")

        # Wyślij decyzję na MQTT (Arduino zacznie to respektować w kolejnym etapie)
        payload = json.dumps({"set_active": int(action)})
        self._client.publish(self.action_topic, payload)

        # Czekamy na kolejną obserwację
        obs = self._wait_for_obs()
        self._step += 1

        # Reward: minimalizuj sumę aut
        reward = -float(np.sum(obs["cars"]))
        self._episode_reward += reward

        terminated = False
        truncated = False
        info = {
            "step": self._step,
            "episode_reward": self._episode_reward,
        }
        return obs, reward, terminated, truncated, info

    def render(self):
        obs = self._last_obs
        if obs is None:
            print("[TrafficLightEnv] No observation to render.")
            return

        parts = []
        for i in range(self.num_lights):
            s = obs["state"][i]
            cars = obs["cars"][i]
            dur = obs["duration"][i]
            parts.append(f"TL{i}: cars={cars}, state={s}, dur={dur}ms")
        print(f"[step={self._step}] " + " | ".join(parts))

    def close(self):
        try:
            self._client.loop_stop()
            self._client.disconnect()
        except Exception:
            pass