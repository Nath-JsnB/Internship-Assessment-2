from flask import Flask, request, jsonify, Response
import threading
import time

app = Flask(__name__)

HVAC_API_USER = "apiuser"
HVAC_API_PASS = "apipassword"

# In-memory status storage
room_status = {
    "room1": "inactive",
    "room2": "inactive",
    "room3": "inactive",
    "room4": "inactive",
    "room5": "inactive",
}

def check_auth(username, password):
    return username == HVAC_API_USER and password == HVAC_API_PASS

def authenticate():
    return Response(
        'Could not verify your access level for that URL.\n'
        'You have to login with proper credentials', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'}
    )

def requires_auth(f):
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    decorated.__name__ = f.__name__
    return decorated

@app.route("/api/hvac/<room>/status", methods=["GET"])
@requires_auth
def get_status(room):
    if room not in room_status:
        return jsonify({"error": "Room not found"}), 404
    return jsonify({"room": room, "status": room_status[room]}), 200

@app.route("/api/hvac/<room>/command", methods=["POST"])
@requires_auth
def command(room):
    if room not in room_status:
        return jsonify({"error": "Room not found"}), 404
    data = request.get_json(silent=True)
    if not data or "command" not in data:
        return jsonify({"error": "Missing 'command' in request body"}), 400

    command = data["command"]
    if command not in ["activate", "deactivate"]:
        return jsonify({"error": "Invalid command"}), 400

    # Simulate processing delay and possible intermittent downtime
    try:
        # Randomly simulate downtime for demonstration (remove in production)
        # import random
        # if random.random() < 0.05:
        #     time.sleep(5)
        #     return jsonify({"error": "Simulated API downtime"}), 503

        room_status[room] = "active" if command == "activate" else "inactive"
        return jsonify({"room": room, "status": room_status[room]}), 200
    except Exception as e:
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({"error": "Method not allowed"}), 405

@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)