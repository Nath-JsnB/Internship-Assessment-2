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

MQTT_BROKER = "localhost"
MQTT_PORT = 1883
ROOMS = ["room1", "room2", "room3", "room4", "room5"]
TEMP_TOPICS = [f"building/{room}/temperature" for room in ROOMS]

LEGACY_API_BASE = "http://localhost:5000/api/hvac"
POLL_INTERVAL = 1  # Faster polling for more responsive control

LOG_FILE = "middleware_actions.log"

HVAC_API_USER = "apiuser"
HVAC_API_PASS = "apipassword"
AUTH = HTTPBasicAuth(HVAC_API_USER, HVAC_API_PASS)

# Optional edge case settings
API_RETRY_LIMIT = 3
API_RETRY_DELAY = 1  # seconds between retries
INVALID_DATA_LIMIT = 3  # Mark error after N consecutive invalid readings

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

class MiddlewareService:
    def __init__(self):
        self.temperatures = {room: 0.0 for room in ROOMS}
        self.hvac_active = {room: None for room in ROOMS}
        self.invalid_counts = {room: 0 for room in ROOMS}
        self.sensor_error = {room: False for room in ROOMS}
        self.api_error = {room: False for room in ROOMS}
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_disconnect = self.on_disconnect
        self.mqtt_client.on_message = self.on_message

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("Middleware connected to MQTT broker.")
            for topic in TEMP_TOPICS:
                client.subscribe(topic)
                print(f"Subscribed to {topic}")
        else:
            print("Failed to connect to MQTT broker, code", rc)

    def on_disconnect(self, client, userdata, rc):
        print(f"[WARNING] MQTT disconnected with code {rc}. Attempting reconnect...")
        while True:
            try:
                client.reconnect()
                print("[INFO] MQTT reconnected.")
                break
            except Exception as e:
                print(f"[ERROR] MQTT reconnect failed: {e}")
                time.sleep(2)

    def on_message(self, client, userdata, msg):
        try:
            room = msg.topic.split("/")[1]
            temp = float(msg.payload.decode())
            if not (0 <= temp <= 50):
                raise ValueError("Temperature out of expected range.")
            self.temperatures[room] = temp
            self.invalid_counts[room] = 0
            self.sensor_error[room] = False
            logging.info(f"Received temperature: {temp}°C for {room}")
        except (ValueError, IndexError) as e:
            room = None
            try:
                room = msg.topic.split("/")[1]
            except Exception:
                pass
            if room in self.invalid_counts:
                self.invalid_counts[room] += 1
                if self.invalid_counts[room] >= INVALID_DATA_LIMIT:
                    self.sensor_error[room] = True
                    logging.error(f"Room {room} marked as sensor error due to repeated invalid data.")
            logging.error(f"Invalid temperature data: {msg.payload} on {msg.topic}: {e}")

    def poll_hvac_status(self, room):
        for attempt in range(API_RETRY_LIMIT):
            try:
                resp = requests.get(f"{LEGACY_API_BASE}/{room}/status", auth=AUTH, timeout=2)
                resp.raise_for_status()
                status = resp.json().get("status")
                self.hvac_active[room] = (status == "active")
                self.api_error[room] = False
                logging.info(f"HVAC status for {room}: {status}")
                return
            except requests.RequestException as e:
                logging.error(f"Error polling HVAC status for {room} (attempt {attempt+1}): {e}")
                print(f"[ERROR] Error polling HVAC status for {room} (attempt {attempt+1}): {e}")
                time.sleep(API_RETRY_DELAY)
        # If all retries fail
        self.api_error[room] = True
        logging.error(f"API marked as error for {room} after {API_RETRY_LIMIT} retries.")

    def send_hvac_command(self, room, activate: bool):
        command = "activate" if activate else "deactivate"
        for attempt in range(API_RETRY_LIMIT):
            try:
                resp = requests.post(
                    f"{LEGACY_API_BASE}/{room}/command",
                    json={"command": command},
                    timeout=2,
                    auth=AUTH
                )
                resp.raise_for_status()
                self.api_error[room] = False
                logging.info(f"Sent HVAC command: {command} for {room}, response: {resp.text}")
                print(f"[ACTION] Sent HVAC command: {command} for {room}, response: {resp.text}")
                return
            except requests.RequestException as e:
                logging.error(f"Error sending HVAC command '{command}' for {room} (attempt {attempt+1}): {e}")
                print(f"[ERROR] Error sending HVAC command '{command}' for {room} (attempt {attempt+1}): {e}")
                time.sleep(API_RETRY_DELAY)
        # If all retries fail
        self.api_error[room] = True
        logging.error(f"API marked as error for {room} after {API_RETRY_LIMIT} retries.")

    def run(self):
        self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        thread = threading.Thread(target=self.mqtt_client.loop_forever)
        thread.daemon = True
        thread.start()

        # Poll all room statuses at startup
        for room in ROOMS:
            self.poll_hvac_status(room)

        try:
            while True:
                try:
                    temps = self.temperatures.copy()
                    print("Current temperatures:", temps)
                    for room, temp in temps.items():
                        # Skip rooms with repeated invalid data or API errors
                        if self.sensor_error[room]:
                            print(f"[WARNING] Skipping {room}: sensor error (repeated invalid data)")
                            continue
                        if self.api_error[room]:
                            print(f"[WARNING] Skipping {room}: API error (recent downtime)")
                            continue

                        should_activate = temp > 30
                        print(f"[DEBUG] Room: {room}, Temp: {temp}, Should activate: {should_activate}, HVAC active: {self.hvac_active[room]}")
                        if should_activate and self.hvac_active[room] is not True:
                            print(f"[ACTION] Activating HVAC for {room}")
                            self.send_hvac_command(room, True)
                            self.hvac_active[room] = True
                        elif not should_activate and self.hvac_active[room] is not False:
                            print(f"[ACTION] Deactivating HVAC for {room}")
                            self.send_hvac_command(room, False)
                            self.hvac_active[room] = False
                    time.sleep(POLL_INTERVAL)
                except Exception as e:
                    logging.error(f"Exception in main loop: {e}", exc_info=True)
                    print(f"[ERROR] Exception in main loop: {e}")
        except KeyboardInterrupt:
            print("Middleware stopped.")

if __name__ == "__main__":
    MiddlewareService().run()