# Import the Paho MQTT client library and alias it as mqtt
import paho.mqtt.client as mqtt

# Set the MQTT broker address (localhost for local testing)
MQTT_BROKER = "localhost"
# Set the MQTT broker port (default MQTT port is 1883)
MQTT_PORT = 1883
# List of room names to listen for HVAC commands
ROOMS = ["room1", "room2", "room3", "room4", "room5"]

def on_connect(client, userdata, flags, rc):
    """
    Callback function executed when the client connects to the broker.
    - client: the client instance for this callback
    - userdata: the private user data as set in Client() or userdata_set()
    - flags: response flags sent by the broker
    - rc: the connection result (0 means success)
    """
    if rc == 0:
        # Connection successful
        print("Connected to MQTT broker.")
        # Subscribe to the HVAC command topic for each room
        for room in ROOMS:
            topic = f"building/{room}/hvac/cmd"     # Constructs the MQTT topic string for each room where HVAC commands will be received. For example, the topic might be "building/room1/hvac/cmd"
            client.subscribe(topic)                 # Subscribes the MQTT client to the HVAC command topic for the current room. This allows the client to receive messages published to this topic
            print(f"Subscribed to {topic}")         # Prints a message indicating that the client has successfully subscribed to the topic.
    else:
        # Connection failed
        print(f"Failed to connect to MQTT broker, code {rc}")

def on_message(client, userdata, msg):
    """
    Callback function executed when a message is received from the broker.
    - client: the client instance for this callback
    - userdata: the private user data as set in Client() or userdata_set()
    - msg: an instance of MQTTMessage, contains topic and payload
    """
    # Extract the room name from the topic (second element after splitting by '/')
    try:
        room = msg.topic.split("/")[1]
    except IndexError:
        room = "invalid"
    # Decode the payload (assumed to be a command string, e.g., "ON" or "OFF")
    try:
        command = msg.payload.decode()
    except Exception:
        command = ""
    # Check if the command is valid ("ON" or "OFF", case-insensitive)
    if command.upper() in ["ON", "OFF"]:
        print(f"Room {room}: HVAC command received: {command}")
    else:
        print(f"Room {room}: Invalid command received: {command}")

def main():
    # Create a new MQTT client instance
    client = mqtt.Client()
    # Assign the on_connect callback
    client.on_connect = on_connect
    # Assign the on_message callback
    client.on_message = on_message

    # Connect to the MQTT broker
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    # Start the network loop and block forever to wait for messages and events
    client.loop_forever()

# Run the main function if this script is executed directly
if __name__ == "__main__":
    main()