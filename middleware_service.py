"""
Middleware Service for Per-Room HVAC Control with Basic Auth & Error Handling
Improved: Better diagnostics, exception handling, and responsive timeouts.
Optional edge cases: API retry, mark error states, MQTT disconnect handling.
"""

import time
import logging
import threading
import requests
import paho.mqtt.client as mqtt
from requests.auth import HTTPBasicAuth

# MQTT broker address and port
MQTT_Broker = "localhost"
MQTT_Port = 1883

# List of rooms to manage
ROOMS = ["room1", "room2", "room3", "room4", "room5"]

# List of temperature topics for each room
Temp_Topics = [f"building/{room}/temperature" for room in ROOMS]

# Base URL for legacy HVAC API
Legacy_API_Base = "http://localhost:5000/api/hvac"

# How often to poll in seconds
Poll_Interval = 1

# Log file for middleware actions
Log_File = "middleware_actions.log"

# API credentials for legacy HVAC API
HVAC_API_User = "apiuser"
HVAC_API_Pass = "apipassword"

# HTTP Basic Auth object for API requests
AUTH = HTTPBasicAuth(HVAC_API_User, HVAC_API_Pass)

# Retry limit and delay for API interactions
API_Rerty_Limit = 3
API_Retry_Delay = 1

# How many invalid data points before marking a sensor as error
Invalid_Data_Limit = 3

# Configure logging to file with timestamps
logging.basicConfig(
    filename=Log_File,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

class MiddlewareService:
    def __init__(self):
        # Store latest temperature readings per room
        self.temperatures = {room: 0.0 for room in ROOMS}
        # Track whether HVAC is currently active per room
        self.hvac_active = {room: None for room in ROOMS}
        # Count invalid data points per room
        self.invalid_counts = {room: 0 for room in ROOMS}
        # Track if a room's sensor is in error state
        self.sensor_error = {room: False for room in ROOMS}
        # Track if a room's API is in error state
        self.api_error = {room: False for room in ROOMS}
        # Create MQTT client instance
        self.mqtt_client = mqtt.Client(client_id="Middleware_Service")
        # Add the Basic Auth Username and Password
        self.mqtt_client.username_pw_set("apiuser", "apipassword")
        # Assign MQTT event handlers
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_disconnect = self.on_disconnect
        self.mqtt_client.on_message = self.on_message

    def on_connect(self, client, userdata, flags, rc):
        # Callback for when MQTT client connects
        if rc == 0:
            print("Middleware connected to MQTT broker.")
            # Subscribe to all temperature topics
            for topic in Temp_Topics:
                client.subscribe(topic)
                print(f"Subscribed to {topic}")
        else:
            print("Failed to connect to MQTT broker, code", rc)

    def on_disconnect(self, client, userdata, rc):
        # Callback for when MQTT client disconnects
        print(f"[WARNING] MQTT disconnected with code {rc}. Attempting reconnect...")
        while True:
            try:
                # Attempt to reconnect until successful
                client.reconnect()
                print("[INFO] MQTT reconnected.")
                break
            except Exception as e:
                print(f"[ERROR] MQTT reconnect failed: {e}")
                time.sleep(2)

    def on_message(self, client, userdata, msg):
        # Callback for handling received MQTT messages
        try:
            # Extract room from topic
            room = msg.topic.split("/")[1]
            # Parse temperature value from payload
            temp = float(msg.payload.decode())
            # Check if temperature is in valid range
            if not (0 <= temp <= 50):
                raise ValueError("Temperature out of expected range.")
            # Store valid temperature, reset error counters
            self.temperatures[room] = temp
            self.invalid_counts[room] = 0
            self.sensor_error[room] = False
            logging.info(f"Received temperature: {temp}°C for {room}")
        except (ValueError, IndexError) as e:
            # Handle invalid temperature or topic format
            room = None
            try:
                room = msg.topic.split("/")[1]
            except Exception:
                pass
            # Increment invalid count and mark sensor error if above threshold
            if room in self.invalid_counts:
                self.invalid_counts[room] += 1
                if self.invalid_counts[room] >= Invalid_Data_Limit:
                    self.sensor_error[room] = True
                    logging.error(f"Room {room} marked as sensor error due to repeated invalid data.")
            logging.error(f"Invalid temperature data: {msg.payload} on {msg.topic}: {e}")

    def poll_hvac_status(self, room):
        # Poll the HVAC status for a given room from the API
        try:
            for attempt in range(API_Rerty_Limit):
                try:
                    # Make a GET request to the status endpoint
                    resp = requests.get(f"{Legacy_API_Base}/{room}/status", auth=AUTH, timeout=2)
                    resp.raise_for_status()
                    # Parse status from JSON response
                    status = resp.json().get("status")
                    # Update internal state
                    self.hvac_active[room] = (status == "active")
                    self.api_error[room] = False
                    logging.info(f"HVAC status for {room}: {status}")
                    return
                except requests.RequestException as e:
                    logging.error(f"Error polling HVAC status for {room} (attempt {attempt+1}): {e}")
                    print(f"[ERROR] Error polling HVAC status for {room} (attempt {attempt+1}): {e}")
                    time.sleep(API_Retry_Delay)
            # Mark API error if all retries failed
            self.api_error[room] = True
            logging.error(f"API marked as error for {room} after {API_Rerty_Limit} retries.")
        except Exception as e:
            # Catch-all for unexpected polling errors
            print(f"[ERROR] Failed to poll HVAC status for {room}: {e}")
            logging.error(f"Failed to poll HVAC status for {room}: {e}")

    def send_hvac_command(self, room, activate: bool):
        # Send an activate/deactivate command to the HVAC API for a room
        command = "activate" if activate else "deactivate"
        for attempt in range(API_Rerty_Limit):
            try:
                # POST command to API
                resp = requests.post(
                    f"{Legacy_API_Base}/{room}/command",
                    json={"command": command},
                    timeout=2,
                    auth=AUTH
                )
                resp.raise_for_status()
                # Mark API as healthy
                self.api_error[room] = False
                logging.info(f"Sent HVAC command: {command} for {room}, response: {resp.text}")
                print(f"[ACTION] Sent HVAC command: {command} for {room}, response: {resp.text}")
                return
            except requests.RequestException as e:
                # Log request-related errors, retry
                logging.error(f"Error sending HVAC command '{command}' for {room} (attempt {attempt+1}): {e}")
                print(f"[ERROR] Error sending HVAC command '{command}' for {room} (attempt {attempt+1}): {e}")
                time.sleep(API_Retry_Delay)
            except Exception as e:
                # Catch-all for unexpected exceptions, retry
                logging.error(f"Unexpected exception sending HVAC command '{command}' for {room} (attempt {attempt+1}): {e}")
                print(f"[ERROR] Unexpected error sending HVAC command '{command}' for {room} (attempt {attempt+1}): {e}")
                time.sleep(API_Retry_Delay)
        # Mark API as error if all retries failed
        self.api_error[room] = True
        logging.error(f"API marked as error for {room} after {API_Rerty_Limit} retries.")

    def run(self):
        # Connect to MQTT broker and start message loop in a separate thread
        self.mqtt_client.connect(MQTT_Broker, MQTT_Port, 60)
        thread = threading.Thread(target=self.mqtt_client.loop_forever)
        thread.daemon = True
        thread.start()
        # Poll initial HVAC status for all rooms
        for room in ROOMS:
            self.poll_hvac_status(room)
        try:
            while True:
                try:
                    # Copy latest temperature readings
                    temps = self.temperatures.copy()
                    print("Current temperatures:", temps)
                    for room, temp in temps.items():
                        # Skip rooms with sensor or API errors
                        if self.sensor_error[room]:
                            print(f"[WARNING] Skipping {room}: sensor error (repeated invalid data)")
                            continue
                        if self.api_error[room]:
                            print(f"[WARNING] Skipping {room}: API error (recent downtime)")
                            continue
                        # Decide if HVAC should be activated
                        should_activate = temp > 30
                        print(f"[DEBUG] Room: {room}, Temp: {temp}, Should activate: {should_activate}, HVAC active: {self.hvac_active[room]}")
                        # Activate HVAC if needed and not already active
                        if should_activate and self.hvac_active[room] is not True:
                            print(f"[ACTION] Activating HVAC for {room}")
                            self.send_hvac_command(room, True)
                            self.hvac_active[room] = True
                        # Deactivate HVAC if not needed and not already inactive
                        elif not should_activate and self.hvac_active[room] is not False:
                            print(f"[ACTION] Deactivating HVAC for {room}")
                            self.send_hvac_command(room, False)
                            self.hvac_active[room] = False
                    # Wait before next poll iteration
                    time.sleep(Poll_Interval)
                except Exception as e:
                    # Log and print any uncaught exceptions in main loop
                    logging.error(f"Exception in main loop: {e}", exc_info=True)
                    print(f"[ERROR] Exception in main loop: {e}")
        except KeyboardInterrupt:
            # Allow graceful shutdown on Ctrl+C
            print("Middleware stopped.")

if __name__ == "__main__":
    # Start the middleware service if run as main program
    MiddlewareService().run()
