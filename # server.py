# server.py (Flask Notifier)
from flask import Flask, request, jsonify
import threading
import signal
import sys

app = Flask(__name__)
shutdown_flag = threading.Event()

# Coloring function (ANSI escape)
def color_text(text, color="white", bold=False):
    colors = {
        "black": 30, "red": 31, "green": 32, "yellow": 33,
        "blue": 34, "magenta": 35, "cyan": 36, "white": 37
    }
    code = colors.get(color, 37)
    style = 1 if bold else 0
    return f"\033[{style};{code}m{text}\033[0m"

@app.route('/update', methods=['POST'])
def receive_update():
    data = request.get_json()
    if not data:
        print(color_text("⚠️  Error: No JSON data received.", "red", True))
        return jsonify({"error": "No JSON data received"}), 400

    print()
    print(color_text("=== New update received ===", "cyan", True))
    print(color_text(f"📁 Directory: {data.get('path', 'N/A')}", "blue", True))
    print(color_text(f"📝 Description: {data.get('description', 'N/A')}", "magenta", True))
    print(color_text("📋 Summary:", "yellow", True))
    print(color_text(data.get('summary', 'N/A'), "yellow"))
    print(color_text("="*30, "cyan"))
    return jsonify({"status": "received"}), 200

@app.route('/bye', methods=['POST'])
def shutdown():
    def shutdown_server():
        shutdown_flag.set()
        func = request.environ.get('werkzeug.server.shutdown')
        if func:
            func()
    threading.Thread(target=shutdown_server).start()
    return "Server shutting down...", 200

def signal_handler(sig, frame):
    print(color_text("\nReceived interrupt signal, shutting down server...", "red", True))
    shutdown_flag.set()
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    print(color_text("🚀 Flask receiver started on http://0.0.0.0:8000", "green", True))
    app.run(host="0.0.0.0", port=8000)