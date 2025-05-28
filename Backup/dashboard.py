from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO, emit
import threading
import time

# Use this import if your middleware is running in the same process, or
# replace with MQTT client code to update temps from the broker.
import middleware_service

app = Flask(__name__)
socketio = SocketIO(app)

# Shared state with the middleware
middleware = middleware_service.MiddlewareService()

# Flask route for main dashboard page
@app.route("/")
def index():
    return render_template("dashboard.html")

# API endpoint for current status (for initial load)
@app.route("/api/status")
def api_status():
    state = {
        "temperatures": middleware.temperatures,
        "hvac_active": middleware.hvac_active,
        "sensor_error": middleware.sensor_error,
        "api_error": middleware.api_error,
    }
    return jsonify(state)

# Periodically emit updates to all clients via SocketIO
def background_broadcast():
    while True:
        state = {
            "temperatures": middleware.temperatures,
            "hvac_active": middleware.hvac_active,
            "sensor_error": middleware.sensor_error,
            "api_error": middleware.api_error,
        }
        socketio.emit("update", state)
        time.sleep(2)

# Run the middleware in a background thread
def start_middleware():
    t = threading.Thread(target=middleware.run)
    t.daemon = True
    t.start()

if __name__ == "__main__":
    # Start middleware, then background broadcaster
    start_middleware()
    socketio.start_background_task(background_broadcast)
    socketio.run(app, host="0.0.0.0", port=8080)