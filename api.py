
from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

latest_reading = {}


@app.route("/api/sensors/readings", methods=["POST"])
def receive_reading():
    global latest_reading

    data = request.get_json(silent=True)

    if not data or not data.get("sensorId"):
        return jsonify({"error": "Missing sensorId"}), 400

    latest_reading = {
        **data,
        "timestamp": datetime.now().isoformat()
    }

    print("Received sensor data:", latest_reading)

    return jsonify({
        "message": "Sensor data received successfully"
    }), 201


@app.route("/api/sensors/readings", methods=["GET"])
def get_reading():
    return jsonify(latest_reading)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
