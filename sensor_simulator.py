# Import the time module for sleep/delays
import time
# Import the random module for generating random numbers
import random
# Import the Paho MQTT client library and alias it as mqtt
import paho.mqtt.client as mqtt

# Define the hostname or IP address of the MQTT broker
MQTT_Broker = "localhost"
# Define the port number for the MQTT broker (default for MQTT is 1883)
MQTT_Port = 1883
# List of room names to simulate temperature sensors for
ROOMS = ["room1", "room2", "room3", "room4", "room5"]
# Interval (in seconds) between publishing temperature updates
Publish_Interval = 10  # seconds

def main():
    # Create a new MQTT client instance
    client = mqtt.Client(client_id="Sensor_Simulator")
    # Connect to the MQTT broker
    client.connect(MQTT_Broker, MQTT_Port, 60)
    # Start a separate thread to handle network events and keep connection alive
    client.loop_start()

    # Initialize the starting temperatures for each room to a value between 28 and 32°C
    current_temps = {room: random.uniform(28, 32) for room in ROOMS}

    try:
        # Main loop: run indefinitely until interrupted
        while True:
            # Iterate over each room to simulate temperature changes and publish
            for room in ROOMS:
                # Simulate a regular temperature drift (can go up or down)
                delta = random.uniform(-1.2, 1.2)
                # Occasionally simulate a "heat wave" with a 10% chance
                if random.random() < 0.10:  # 10% chance
                    delta += random.uniform(2, 4)
                # Update the current temperature, keeping it within 15°C and 35°C
                current_temps[room] = max(15, min(35, current_temps[room] + delta))
                # Round the temperature to two decimal places for publishing
                temp = round(current_temps[room], 2)
                # Construct the MQTT topic for this room's temperature
                topic = f"building/{room}/temperature"
                # Convert the temperature value to a string to send as payload
                payload = str(temp)
                # Publish the temperature to the MQTT broker on the constructed topic
                client.publish(topic, payload)
                # Print a confirmation message to the console
                print(f"Published: {payload}°C to {topic}")
            # Wait for the defined interval before publishing the next set of temperatures
            time.sleep(Publish_Interval)
    except KeyboardInterrupt:
        # If the user stops the script (e.g., with Ctrl+C), print a message
        print("Sensor simulation stopped.")
    finally:
        # Stop the MQTT network loop and disconnect cleanly
        client.loop_stop()
        client.disconnect()

# Run the main function if this script is executed directly
if __name__ == "__main__":
    main()
