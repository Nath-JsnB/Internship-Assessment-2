import paho.mqtt.client as mqtt

MQTT_BROKER = "localhost"
MQTT_PORT = 1883
ROOMS = ["room1", "room2", "room3", "room4", "room5"]

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT broker.")
        for room in ROOMS:
            topic = f"building/{room}/hvac/cmd"
            client.subscribe(topic)
            print(f"Subscribed to {topic}")
    else:
        print(f"Failed to connect, return code {rc}")

def on_message(client, userdata, msg):
    room = msg.topic.split("/")[1]
    command = msg.payload.decode()
    if command.upper() in ["ON", "OFF"]:
        print(f"Room {room}: HVAC command received: {command}")
    else:
        print(f"Room {room}: Invalid command received: {command}")

def main():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_forever()

if __name__ == "__main__":
    main()