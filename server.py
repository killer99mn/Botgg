from flask import Flask, request, jsonify, send_from_directory
from flask_sock import Sock
import time

app = Flask(__name__, static_folder="static")
sock = Sock(app)

clients = []

@app.route("/")
def home():
    return send_from_directory("static", "index.html")

# WebSocket
@sock.route("/ws")
def ws(ws):
    clients.append(ws)
    while True:
        try:
            msg = ws.receive()
            if msg:
                for c in clients:
                    try:
                        c.send(msg)
                    except:
                        pass
        except:
            break

# HTTP fallback (long polling)
@app.route("/poll", methods=["POST"])
def poll():
    msg = request.json.get("msg")
    if msg:
        for c in clients:
            try:
                c.send(msg)
            except:
                pass
    return jsonify({"ok": True})

app.run(host="0.0.0.0", port=5000)
