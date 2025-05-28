# Import Flask for web server, render_template for serving HTML, and jsonify for JSON API responses
from flask import Flask, render_template, jsonify
# Import Flask-SocketIO for real-time bi-directional communication with clients
from flask_socketio import SocketIO, emit
# Import threading for running background tasks
import threading
# Import time for sleep/delays
import time

# Import the middleware service that manages shared state
# (If middleware is external, this would be replaced by MQTT client code)
import middleware_service

# Create a Flask web application instance
app = Flask(__name__)
# Create a SocketIO instance for real-time communication, wrapping the Flask app
socketio = SocketIO(app)

# Create a middleware service instance to access shared HVAC and sensor state
middleware = middleware_service.MiddlewareService()

# Define the Flask route for the main dashboard page
@app.route("/")
def index():
    # Render and return the dashboard.html template to the client
    return render_template("dashboard.html")

# Define an API endpoint to return the current HVAC/sensor status as JSON
@app.route("/api/status")
def api_status():
    # Package up the current state from the middleware
    state = {
        "temperatures": middleware.temperatures,   # Dictionary of room temperatures
        "hvac_active": middleware.hvac_active,     # Dictionary of HVAC status by room
        "sensor_error": middleware.sensor_error,   # Boolean for sensor error state
        "api_error": middleware.api_error,         # Boolean for API error state
    }
    # Respond to the client with the state as JSON
    return jsonify(state)

# Function to periodically broadcast state updates to all connected SocketIO clients
def background_broadcast():
    while True:
        # Prepare the current state for broadcasting
        state = {
            "temperatures": middleware.temperatures,
            "hvac_active": middleware.hvac_active,
            "sensor_error": middleware.sensor_error,
            "api_error": middleware.api_error,
        }
        # Emit an 'update' event with the state to all clients
        socketio.emit("update", state)
        # Wait for 2 seconds before sending the next update
        time.sleep(2)

# Function to run the middleware service in a background daemon thread
def start_middleware():
    t = threading.Thread(target=middleware.run)  # Create a thread to run the middleware's run() method
    t.daemon = True                             # Set as a daemon so it exits with the main program
    t.start()                                   # Start the thread

# Run this block only if the script is executed directly
if __name__ == "__main__":
    # Start the middleware service in a background thread
    start_middleware()
    # Start the state broadcasting task in a background thread
    socketio.start_background_task(background_broadcast)
    # Run the Flask application with SocketIO on all interfaces, port 8080
    socketio.run(app, host="0.0.0.0", port=8080)