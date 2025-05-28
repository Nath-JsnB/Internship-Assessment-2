import time
import random
import paho.mqtt.client as mqtt

MQTT_BROKER = "localhost"
MQTT_PORT = 1883
ROOMS = ["room1", "room2", "room3", "room4", "room5"]
PUBLISH_INTERVAL = 10  # seconds

def main():
    client = mqtt.Client()
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()

    # Start closer to 28-32°C
    current_temps = {room: random.uniform(28, 32) for room in ROOMS}

    try:
        while True:
            for room in ROOMS:
                # Regular drift, faster change
                delta = random.uniform(-1.2, 1.2)
                # Occasional heat wave
                if random.random() < 0.10:  # 10% chance
                    delta += random.uniform(2, 4)
                current_temps[room] = max(15, min(35, current_temps[room] + delta))
                temp = round(current_temps[room], 2)
                topic = f"building/{room}/temperature"
                payload = str(temp)
                client.publish(topic, payload)
                print(f"Published: {payload}°C to {topic}")
            time.sleep(PUBLISH_INTERVAL)
    except KeyboardInterrupt:
        print("Sensor simulation stopped.")
    finally:
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main()