"""
Simple in-memory Flask API for EcoTwin.
Run:
    python api.py

No MongoDB is required. Data is lost when this process stops.
The ESP32 POSTs JSON; Streamlit GETs the latest reading.
"""
from datetime import datetime, timezone
from flask import Flask, jsonify, request

app = Flask(__name__)
latest_reading = None

@app.route("/api/sensors/readings", methods=["GET", "POST"])
def sensor_readings():
    global latest_reading

    if request.method == "POST":
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify({"error": "Expected a JSON object"}), 400

        soil = payload.get("Soil Moisture", payload.get("soil_moisture"))
        light = payload.get("Light", payload.get("light"))
        if soil is None or light is None:
            return jsonify({
                "error": 'JSON must contain "Soil Moisture" and "Light"'
            }), 400

        try:
            soil = float(soil)
            light = float(light)
        except (TypeError, ValueError):
            return jsonify({"error": "Sensor values must be numeric"}), 400

        if not (0 <= soil <= 100 and 0 <= light <= 100):
            return jsonify({"error": "Expected percentages from 0 to 100"}), 400

        latest_reading = {
            "Soil Moisture": soil,
            "Light": light,
            "received_at": datetime.now(timezone.utc).isoformat()
        }
        return jsonify({"message": "Reading received", "reading": latest_reading}), 201

    return jsonify(latest_reading or {})

if __name__ == "__main__":
    # 0.0.0.0 allows the ESP32 on your Wi-Fi network to reach this server.
    app.run(host="0.0.0.0", port=5000, debug=False)
