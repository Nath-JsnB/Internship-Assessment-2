# Per-Room HVAC Control System

This project integrates a legacy REST API with modern MQTT-based IoT sensors to demonstrate a comprehensive, safe, and reliable middleware system for HVAC control and per-room temperature monitoring.

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

- **MQTT sensors** report on temperature of each room.
- **Middleware** which is the recipient of these readings also controls HVAC in each room via a **REST API**.
- All API endpoints use **HTTP Basic Authentication**.
- The system is robust which is proved by its performance in handling invalid data, network outages, and API outages.
- **Real-Time Monitoring Dashboard:** Real time access to each room’s temperature, HVAC status, and error conditions is available via the live web interface.

---

## How to Run the System

### 1. Prerequisites

- Python 3.7+
- `paho-mqtt`, `requests`, `Flask`, and `flask-socketio` libraries
- An MQTT broker running locally (e.g., [Mosquitto](https://mosquitto.org/))
- All included code files from this repository (`middleware_service.py`, `mock_legacy_api.py`, `dashboard.py`, `actuator_simulator.py`, `sensor_simulator.py`)

You can get the required Python packages with:

```sh
pip install paho-mqtt requests flask flask-socketio eventlet
```
(Before you start, make sure your terminal's current directory (cd) is set.)


### 2. Start All Services (Recommended)

#### **For Windows users**

Run at startup all of the required components (Legacy API, Middleware Service, and Dashboard) from the included batch file:

```bat
Start_All.bat
```

You are able to double click on `Start_All.bat`, or run it from the command prompt. Upon doing so three terminal windows will open each with a different service running in each.

#### **For Linux/macOS users**

On Linux and macOS you may use the provided `start_all.sh` script:

```bash
./start_all.sh
```
Ensure the script is executable:
```bash
chmod +x start_all.sh
```
All services will boot in the background and in that terminal which they are run in you may use `Ctrl+C` to stop them all at once.

---

**Note:**  
At http:/localhost:8880 you will not see any temperature readings until you start the sensor simulator. Go to the next section for instructions.

---

### 3. Simulate MQTT Temperature Sensors

Temperature readings from each room can be published via the included sensor simulation script, also you can use a MQTT client like `mosquitto_pub` to put in test temperatures.

---

### 4. Run Unit Tests

To check that everything is working properly and that error handling is as expected run the included unit tests (see below).

---

### 5. Observe Logs and Actions

- Middleware activity is logged to `middleware_actions.log`.
- Real time operations which include command decisions and error conditions will be displayed on the console.

---

## Sensor Simulator Script

This script is used to simulate temperature sensors for all rooms, which send temperature readings to the MQTT broker at a fixed interval.

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
Published temps will be displayed on the dashboard and in the middleware logs. 
**Temperatures will not display until the simulator is run.**

---

## Real-Time Monitoring Dashboard

You have access to a local web based dashboard which will update you in real time on your simulated data.

### Features

- **Live Updates:**  
  Displays present temperature, HVAC status and also any errors for each room in real time.
- **Web Interface:**  
  Connects with the backend through Flask-SocketIO and WebSockets.
- **Customizable:**  
  Easily scale out with more data, controls, or visualization.

### How to Use

1. **Start the Dashboard Server:**

   ```sh
   python dashboard.py
   ```

2. **Open Your Browser:**  
   Go to [http://localhost:8080](http://localhost:8080)

   A table of rooms and their real-time temperatures and statuses showed be displayed.  
   **Note:** The dashboard will only show room temperatures after the sensor simulator has started publishing data.

3. **Integration:**  
   The dashboard reports on middleware updates and displays the changes. It works in association with present middleware and simulation services. 

#### File Structure

- `dashboard.py` — In dashboard.py we launch the Flask-SocketIO server.
- `templates/dashboard.html` — Web dashboard interface.

---

## Unit Test Scripts

The below set of Unit tests for core components which check out proper authentication, error handling, and logic for the legacy API and middleware service.

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

You can use the middleware and sensor simulator to see:
- Correct HVAC activation and deactivation at threshold crossings.
- Address issues related to error logging which is a result of API or MQTT unreachability.

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

- **MQTT** is used for real time, very lightweight publish/subscribe messaging from room temp sensors to the middleware. Each room’s temperature is published to a separate topic(for example, `building/room1/temperature`).
- **REST API** (HTTP) is used to communicate between the middleware and the legacy HVAC control system:
  - `GET /api/hvac/<room>/status` returns present HVAC status.
  - `POST /api/hvac/<room>/command` command to activate or deactivate HVAC in a room.
- **HTTP Basic Auth** is used for all REST API endpoints to prevent access by unauthorized users.

### Security

- All to use the REST API must present valid HTTP Basic Auth.
- The middleware which handles credentials; we use Python’s `requests` library with `HTTPBasicAuth` for all requests.
- Requests that do not have the right credentials are not processed by the API at all; instead it returns `401 Unauthorized`.

### Error Handling

- **API Downtime:** Timeouts and we use robust try/except logic for all API calls. We retry requests until the room goes into an error state if the legacy API won out. If the API reports back as online the system will auto recover.
- **Invalid Sensor Data:** Valid only sensor readings must be between 0°C to 35°C. If the same invalid reading is reported again the room is put in a sensor error state and skipped out until we get what is a good report.
- **MQTT Disconnects:** If out of connection the middleware will try to reconnect to the MQTT broker.

---

## Directory Structure

```
middleware_service.py        # Main middleware (MQTT+REST integration)
mock_legacy_api.py           # Simulated legacy HVAC REST API (Flask)
sensor_simulator.py          # Simulates multiple room temperature sensors
dashboard.py                 # Flask-SocketIO real-time dashboard server
Start_All.bat                # Batch script to start all main services (Windows)
start_all.sh                 # Shell script to start all main services (Linux/macOS)
templates/
    dashboard.html           # HTML template for the real-time dashboard
test_api_auth.py             # Unit test for API authentication and status
test_invalid_sensor_data.py  # Unit test for invalid sensor data handling
README.md                    # This documentation
middleware_actions.log       # Log file for middleware actions/errors
```

---

## Extending the System

- **Add more rooms:** Update the `ROOMS` array in all related scripts.
- **Change thresholds:** Adjust settings for activation temperature or error handling in `middleware_service.py`.
- **Deploy on multiple machines:** Change out the `MQTT_BROKER` and API URLs as required.
- **Integrate real sensors:** Set up your IoT devices to post to the correct MQTT topics.
- **Expand the dashboard:**  Add to the dashboard as required elements of history charts, alerts, or controls.

---

## Contact

For questions or contributions, please open an issue or pull request on this repository.
