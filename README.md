# Per-Room HVAC Control System

This project demonstrates a complete, secure, and robust middleware system for per-room temperature monitoring and HVAC control, integrating a legacy REST API with modern MQTT-based IoT sensors.

---

## Table of Contents

- [Overview](#overview)
- [How to Run the System](#how-to-run-the-system)
- [Sensor Simulator Script](#sensor-simulator-script)
- [Real-Time Monitoring Dashboard](#real-time-monitoring-dashboard)
- [Unit Test Scripts](#unit-test-scripts)
- [Design Decisions](#design-decisions)
  - [Protocols](#protocols)
  - [Security](#security)
  - [Error Handling](#error-handling)
- [Directory Structure](#directory-structure)
- [Extending the System](#extending-the-system)

---

## Overview

- **MQTT sensors** publish temperature readings for each room.
- **Middleware** subscribes to these readings and controls room HVAC units via a **REST API**.
- All API endpoints are protected using **HTTP Basic Authentication**.
- The system is robust, handling network failures, API downtime, and invalid data gracefully.
- **Real-Time Monitoring Dashboard:** A live web interface provides real-time visibility into every room’s temperature, HVAC status, and any error conditions.

---

## How to Run the System

### 1. Prerequisites

- Python 3.7+
- `paho-mqtt`, `requests`, `Flask`, and `flask-socketio` libraries
- An MQTT broker running locally (e.g., [Mosquitto](https://mosquitto.org/))
- All code files from this repository (`middleware_service.py`, `mock_legacy_api.py`, etc.)

You can install the required Python packages with:

```sh
pip install paho-mqtt requests flask flask-socketio eventlet
```
(Before you begin, ensure your terminals' current directory(cd) is set to where you have extracted the repository files)

### 2. Start the Legacy HVAC API

In one terminal:
```sh
python mock_legacy_api.py
```
The API will listen on `http://localhost:5000`.

### 3. Start the Middleware Service

In another terminal:
```sh
python middleware_service.py
```

### 4. Simulate MQTT Temperature Sensors

You can use the included sensor simulator script (see below), or publish test temperatures using an MQTT client such as `mosquitto_pub`.

### 5. Start the Real-Time Monitoring Dashboard

In a new terminal:
```sh
python dashboard.py
```
Then open [http://localhost:8080](http://localhost:8080) in your browser to monitor room temperatures and HVAC status live.

### 6. Run Unit Tests

You can run the included unit tests to verify correct operation and error handling (see below).

### 7. Observe Logs and Actions

- Middleware actions and errors are logged to `middleware_actions.log`.
- The console will display real-time operations, including command decisions and error conditions.

---

## Sensor Simulator Script

This script simulates temperature sensors for all rooms, publishing random temperature readings to the MQTT broker.

```python name=sensor_simulator.py
import time
import random
import paho.mqtt.client as mqtt

MQTT_BROKER = "localhost"
MQTT_PORT = 1883
ROOMS = ["room1", "room2", "room3", "room4", "room5"]

client = mqtt.Client()
client.connect(MQTT_BROKER, MQTT_PORT, 60)

try:
    while True:
        for room in ROOMS:
            # Simulate a realistic temperature between 18°C and 34°C
            temp = round(random.uniform(18, 34), 1)
            topic = f"building/{room}/temperature"
            client.publish(topic, temp)
            print(f"Published {temp}°C to {topic}")
        time.sleep(2)
except KeyboardInterrupt:
    print("Sensor simulator stopped.")
    client.disconnect()
```

#### **How to use:**
```sh
python sensor_simulator.py
```
You should see published temperatures appearing in your middleware logs and on the dashboard.

---

## Real-Time Monitoring Dashboard

A web-based dashboard is included for live monitoring of your simulated data.

### Features

- **Live Updates:**  
  Displays current temperature, HVAC status, and any errors for each room in real time.
- **Web Interface:**  
  Connects to the backend using Flask-SocketIO and WebSockets.
- **Customizable:**  
  Easily expand with more data, controls, or visualization.

### How to Use

1. **Start the Dashboard Server:**

   ```sh
   python dashboard.py
   ```

2. **Open Your Browser:**  
   Go to [http://localhost:8080](http://localhost:8080)

   You’ll see a table of rooms and their real-time temperatures and statuses.

3. **Integration:**  
   The dashboard listens for updates from the middleware and displays them as they change. It works alongside the existing simulator and middleware services.

#### File Structure

- `dashboard.py` — Launches the Flask-SocketIO server.
- `templates/dashboard.html` — Web dashboard interface.

---

## Unit Test Scripts

The following unit tests verify correct authentication, error handling, and logic for the legacy API and middleware service.

### **Test 1: Legacy API Authentication**

```python name=test_api_auth.py
import requests
from requests.auth import HTTPBasicAuth

BASE = "http://localhost:5000/api/hvac/room1/status"

def test_no_auth():
    r = requests.get(BASE)
    assert r.status_code == 401
    print("PASS: No auth returns 401 Unauthorized")

def test_wrong_auth():
    r = requests.get(BASE, auth=HTTPBasicAuth("baduser", "badpass"))
    assert r.status_code == 401
    print("PASS: Wrong auth returns 401 Unauthorized")

def test_right_auth():
    r = requests.get(BASE, auth=HTTPBasicAuth("apiuser", "apipassword"))
    assert r.status_code == 200
    print("PASS: Right auth returns 200 OK")

if __name__ == "__main__":
    test_no_auth()
    test_wrong_auth()
    test_right_auth()
```

### **Test 2: Middleware Main Logic (Manual/Interactive)**

You can run the middleware and sensor simulator and observe:
- Correct HVAC activation/deactivation when temperatures cross the threshold.
- Correct error logging when API or MQTT is unreachable.

### **Test 3: Invalid Sensor Data Handling**

```python name=test_invalid_sensor_data.py
import paho.mqtt.client as mqtt
import time

MQTT_BROKER = "localhost"
MQTT_PORT = 1883
TOPIC = "building/room1/temperature"

client = mqtt.Client()
client.connect(MQTT_BROKER, MQTT_PORT, 60)

# Send invalid temperatures
invalid_temps = [-10, 100, "notanumber"]
for temp in invalid_temps:
    client.publish(TOPIC, str(temp))
    print(f"Published invalid temperature: {temp} to {TOPIC}")

time.sleep(2)
client.disconnect()
print("Test complete: Check middleware log for error entries.")
```

---

## Design Decisions

### Protocols

- **MQTT** is used for real-time, lightweight publish/subscribe messaging from room temperature sensors to the middleware. Each room's temperature is published to a unique topic (e.g., `building/room1/temperature`).
- **REST API** (HTTP) is used for communication between the middleware and the legacy HVAC control system:
  - `GET /api/hvac/<room>/status` retrieves current HVAC status.
  - `POST /api/hvac/<room>/command` activates or deactivates HVAC for a room.
- **HTTP Basic Auth** secures all REST API endpoints to prevent unauthorized access.

### Security

- The REST API requires valid HTTP Basic Authentication for all endpoints.
- Credentials are managed securely in the middleware; all requests use Python's `requests` library with `HTTPBasicAuth`.
- The API never processes requests without proper credentials, returning `401 Unauthorized` otherwise.

### Error Handling

- **API Downtime:** All API calls use timeouts and robust try/except logic. If the legacy API is unreachable, requests are retried several times before marking the room as in error state. The system automatically recovers if the API comes back online.
- **Invalid Sensor Data:** Sensor readings are validated (must be between 0–35°C). If repeated invalid readings are received, the room is marked with a sensor error state and skipped until valid data arrives.
- **MQTT Disconnects:** The middleware automatically attempts to reconnect to the MQTT broker if disconnected.

---

## Directory Structure

```
middleware_service.py        # Main middleware (MQTT+REST integration)
mock_legacy_api.py           # Simulated legacy HVAC REST API (Flask)
sensor_simulator.py          # Simulates multiple room temperature sensors
dashboard.py                 # Flask-SocketIO real-time dashboard server
templates/
    dashboard.html           # HTML template for the real-time dashboard
test_api_auth.py             # Unit test for API authentication and status
test_invalid_sensor_data.py  # Unit test for invalid sensor data handling
README.md                    # This documentation
middleware_actions.log       # Log file for middleware actions/errors
```

---

## Extending the System

- **Add more rooms:** Update the `ROOMS` list in all relevant scripts.
- **Change thresholds:** Adjust activation temperature or error handling limits in `middleware_service.py`.
- **Deploy on multiple machines:** Change `MQTT_BROKER` and API URLs as appropriate.
- **Integrate real sensors:** Configure your IoT devices to publish to the correct MQTT topics.
- **Expand the dashboard:** Add historical charts, alerts, or controls to the dashboard as needed.

---

## Contact

For questions or contributions, please open an issue or pull request on this repository.