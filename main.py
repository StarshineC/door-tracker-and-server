import json
import os
import threading
import time
from datetime import datetime
from flask import Flask, jsonify, render_template_string
from gpiozero import Button, DistanceSensor, LED

app = Flask(__name__)

# --- Hardware Configuration (BCM Pins) ---
sensor = DistanceSensor(echo=17, trigger=27, max_distance=2.0)
door_led = LED(18)
reset_button = Button(22, pull_up=True, bounce_time=0.2)

DATA_FILE = "door_stats.json"
DELTA_THRESHOLD_M = 0.15  # 15 cm change above baseline indicates OPEN
lock = threading.Lock()

# --- State Storage ---
baseline_distance = 0.10  # Default initial baseline in meters

tracker_data = {
    "current_state": "Closed",
    "baseline_cm": 10.0,
    "session_open_count": 0,
    "all_time_open_count": 0,
    "events": [],
}


def load_persistent_stats():
    """Load all-time statistics and history from JSON file."""
    global tracker_data
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                saved = json.load(f)
                tracker_data["all_time_open_count"] = saved.get(
                    "all_time_open_count", 0
                )
                tracker_data["events"] = saved.get("events", [])
        except Exception as e:
            print(f"Error loading saved data: {e}")


def save_persistent_stats():
    """Save all-time count and timestamps to JSON file."""
    with lock:
        save_dict = {
            "all_time_open_count": tracker_data["all_time_open_count"],
            "events": tracker_data["events"],
        }
        try:
            with open(DATA_FILE, "w") as f:
                json.dump(save_dict, f, indent=2)
        except Exception as e:
            print(f"Error saving data: {e}")


def calibrate_baseline():
    """Recalibrates the closed baseline distance when the button is pressed."""
    global baseline_distance, tracker_data
    current_dist = sensor.distance
    with lock:
        baseline_distance = current_dist
        tracker_data["baseline_cm"] = round(current_dist * 100, 1)
    print(f"[CALIBRATED] New 'Closed' Baseline set to: {tracker_data['baseline_cm']} cm")


# Attach push button to baseline calibration function
reset_button.when_pressed = calibrate_baseline


def monitor_door():
    """Background monitoring loop for door state detection."""
    global tracker_data, baseline_distance
    is_open = False

    time.sleep(0.5)
    calibrate_baseline()  # Auto-calibrate baseline on startup

    while True:
        dist = sensor.distance

        with lock:
            target_baseline = baseline_distance

        # Check if measured distance exceeds baseline + threshold
        if dist > (target_baseline + DELTA_THRESHOLD_M) and not is_open:
            is_open = True
            door_led.on()  # Turn LED ON when door is open
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            with lock:
                tracker_data["session_open_count"] += 1
                tracker_data["all_time_open_count"] += 1
                tracker_data["current_state"] = "Open"
                tracker_data["events"].append(
                    {"event": "Door Opened", "time": timestamp}
                )

            save_persistent_stats()
            print(f"[{timestamp}] Door OPENED (Session: {tracker_data['session_open_count']}, All-time: {tracker_data['all_time_open_count']})")

        elif dist <= (target_baseline + DELTA_THRESHOLD_M) and is_open:
            is_open = False
            door_led.off()  # Turn LED OFF when door is closed
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            with lock:
                tracker_data["current_state"] = "Closed"

            print(f"[{timestamp}] Door CLOSED")

        time.sleep(0.1)


# --- HTML Dashboard Template ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Raspberry Pi Door Tracker</title>
    <meta http-equiv="refresh" content="2">
    <style>
        body { font-family: Arial, sans-serif; margin: 30px; background-color: #f8f9fa; }
        .card { background: white; padding: 25px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); max-width: 650px; }
        .badge-open { color: #dc3545; font-weight: bold; font-size: 24px; }
        .badge-closed { color: #28a745; font-weight: bold; font-size: 24px; }
        .stats-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin: 20px 0; }
        .stat-box { background: #e9ecef; padding: 15px; border-radius: 8px; text-align: center; }
        .stat-number { font-size: 28px; font-weight: bold; color: #007bff; }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; }
        th, td { padding: 10px; border: 1px solid #dee2e6; text-align: left; }
        th { background-color: #343a40; color: white; }
    </style>
</head>
<body>
    <div class="card">
        <h2>🚪 Smart Door Tracker Dashboard</h2>
        <p>Current Status: 
            <span class="{{ 'badge-open' if data.current_state == 'Open' else 'badge-closed' }}">
                {{ data.current_state.upper() }}
            </span>
        </p>
        <p><em>Current Calibrated Baseline: <strong>{{ data.baseline_cm }} cm</strong></em></p>
        
        <div class="stats-grid">
            <div class="stat-box">
                <div>Session Door Opens</div>
                <div class="stat-number">{{ data.session_open_count }}</div>
            </div>
            <div class="stat-box">
                <div>All-Time Door Opens</div>
                <div class="stat-number">{{ data.all_time_open_count }}</div>
            </div>
        </div>

        <h3>Recent Open Timestamps</h3>
        <table>
            <tr><th>#</th><th>Event</th><th>Timestamp</th></tr>
            {% for ev in data.events[::-1] %}
            <tr>
                <td>{{ loop.revindex }}</td>
                <td>{{ ev.event }}</td>
                <td>{{ ev.time }}</td>
            </tr>
            {% else %}
            <tr><td colspan="3">No door open events recorded yet.</td></tr>
            {% endfor %}
        </table>
    </div>
</body>
</html>
"""


@app.route("/")
def index():
    with lock:
        return render_template_string(HTML_TEMPLATE, data=tracker_data)


@app.route("/api/status")
def api_status():
    with lock:
        return jsonify(tracker_data)


if __name__ == "__main__":
    load_persistent_stats()

    # Start hardware monitoring in a separate daemon thread
    monitor_thread = threading.Thread(target=monitor_door, daemon=True)
    monitor_thread.start()

    # Launch Flask server on port 5000 accessible across the local network
    app.run(host="0.0.0.0", port=5000)
