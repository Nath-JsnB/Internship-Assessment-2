# Import required modules from Flask for web API functionality
from flask import Flask, request, jsonify, Response
# Import threading (not used directly here, but often for background tasks)
import threading
# Import time module for simulating delays
import time

# Create a Flask web application instance
app = Flask(__name__)

# Define the hardcoded username and password for API authentication
HVAC_API_USER = "apiuser"
HVAC_API_PASS = "apipassword"

# Store the status ("active"/"inactive") of each room in memory
room_status = {
    "room1": "inactive",
    "room2": "inactive",
    "room3": "inactive",
    "room4": "inactive",
    "room5": "inactive",
}

def check_auth(username, password):
    """
    Return True if the provided username and password match the expected credentials.
    """
    return username == HVAC_API_USER and password == HVAC_API_PASS

def authenticate():
    """
    Return a 401 Unauthorized response with a WWW-Authenticate header to trigger basic auth in clients.
    """
    return Response(
        'Could not verify your access level for that URL.\n'
        'You have to login with proper credentials', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'}
    )

def requires_auth(f):
    """
    Decorator function to enforce HTTP Basic authentication on API endpoints.
    """
    def decorated(*args, **kwargs):
        # Get the authorization data from the request
        auth = request.authorization
        # If no auth or bad credentials, force client to authenticate
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        # Call the original (decorated) function
        return f(*args, **kwargs)
    # Ensure the wrapped function preserves its original name
    decorated.__name__ = f.__name__
    return decorated

@app.route("/api/hvac/<room>/status", methods=["GET"])
@requires_auth
def get_status(room):
    """
    Endpoint to get the current HVAC status of a room.
    Requires authentication.
    """
    # If the room doesn't exist, return a 404 error
    if room not in room_status:
        return jsonify({"error": "Room not found"}), 404
    # Return the current status of the room
    return jsonify({"room": room, "status": room_status[room]}), 200

@app.route("/api/hvac/<room>/command", methods=["POST"])
@requires_auth
def command(room):
    """
    Endpoint to activate or deactivate HVAC for a room.
    Requires authentication and a JSON body with 'command'.
    """
    # If the room doesn't exist, return a 404 error
    if room not in room_status:
        return jsonify({"error": "Room not found"}), 404
    # Parse the JSON body of the request
    data = request.get_json(silent=True)
    # If no JSON or 'command' missing, return a 400 error
    if not data or "command" not in data:
        return jsonify({"error": "Missing 'command' in request body"}), 400

    # Extract the command value from the request
    command = data["command"]
    # Only allow "activate" or "deactivate" commands
    if command not in ["activate", "deactivate"]:
        return jsonify({"error": "Invalid command"}), 400

    # Simulate processing delay and possible intermittent downtime (commented out)
    try:
        # This block could be uncommented to randomly simulate API downtime for demo purposes
        # import random
        # if random.random() < 0.05:
        #     time.sleep(5)
        #     return jsonify({"error": "Simulated API downtime"}), 503

        # Set the room status based on the command
        room_status[room] = "active" if command == "activate" else "inactive"
        # Return the new status of the room
        return jsonify({"room": room, "status": room_status[room]}), 200
    except Exception as e:
        # Return a 500 error if an exception occurs
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

@app.errorhandler(404)
def not_found(e):
    """
    Return a JSON 404 error for undefined endpoints.
    """
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(405)
def method_not_allowed(e):
    """
    Return a JSON 405 error for methods not allowed on a route.
    """
    return jsonify({"error": "Method not allowed"}), 405

@app.errorhandler(500)
def internal_error(e):
    """
    Return a JSON 500 error for internal server errors.
    """
    return jsonify({"error": "Internal server error"}), 500

# Start the Flask application if this script is run directly
if __name__ == "__main__":
    # Run on all interfaces (0.0.0.0), port 5000, with debug mode enabled
    app.run(host="0.0.0.0", port=5000, debug=True)
