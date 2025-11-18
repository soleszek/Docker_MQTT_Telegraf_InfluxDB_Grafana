import paho.mqtt.client as mqtt
import time
import os

MQTT_BROKER_HOST = os.environ.get('MQTT_HOST', 'mosquitto') 
MQTT_BROKER_PORT = 1883
TIME_TOPIC = "system/time/unix"

def mqtt_time_publisher():
    client = mqtt.Client()
    
    while True:
        try:
            client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, 60)
            print(f"✅ MQTT Time Publisher connected to {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}")
            
            client.loop_start() 

            while client.is_connected():
                current_time_ms = int(time.time() * 1000)
                
                client.publish(TIME_TOPIC, str(current_time_ms), qos=1)
                
                time.sleep(1) 

            client.loop_stop()
        
        except Exception as e:
            print(f"❌ Connection or publish error: {e}. Retrying connection in 5 seconds...")
            time.sleep(5)

if __name__ == '__main__':
    mqtt_time_publisher()