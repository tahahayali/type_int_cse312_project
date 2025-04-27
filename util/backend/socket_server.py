from flask import Flask, request
from flask_socketio import SocketIO, emit
import random
import eventlet

eventlet.monkey_patch()

MAP_SEED = random.randint(0, 2**32 - 1)   # one deterministic seed

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret"
socketio = SocketIO(app, cors_allowed_origins="*")

players = {}   # sid → {x, y, it, name}


@app.route("/")
def index():
    return "Socket.IO server running"


@socketio.on("connect")
def handle_connect():
    sid       = request.sid
    username  = request.args.get("username", f"user-{sid[:4]}")
    spawn_x   = random.randint(64, 700)
    spawn_y   = random.randint(64, 500)
    is_it     = len(players) == 0

    players[sid] = {"x": spawn_x, "y": spawn_y, "it": is_it, "name": username}

    emit("init", {"id": sid, "seed": MAP_SEED, "players": players})
    emit("playerJoined",
         {"id": sid, "x": spawn_x, "y": spawn_y, "it": is_it, "name": username},
         broadcast=True, include_self=False)


@socketio.on("move")
def handle_move(data):
    sid = request.sid
    if sid in players:
        players[sid]["x"] = data["x"]
        players[sid]["y"] = data["y"]
        emit("playerMoved", {"id": sid, "x": data["x"], "y": data["y"]},
             broadcast=True)


@socketio.on("tag")
def handle_tag(data):
    tagger = request.sid
    target = data.get("id")
    if tagger in players and target in players and players[tagger]["it"]:
        players[tagger]["it"] = False
        players[target]["it"] = True
        emit("tagUpdate", {"newIt": target, "prevIt": tagger}, broadcast=True)


@socketio.on("disconnect")
def handle_disconnect():
    sid    = request.sid
    was_it = players.get(sid, {}).get("it", False)
    if sid in players:
        del players[sid]
    emit("playerLeft", {"id": sid}, broadcast=True)

    if was_it and players:
        new_it = random.choice(list(players.keys()))
        players[new_it]["it"] = True
        emit("tagUpdate", {"newIt": new_it, "prevIt": sid}, broadcast=True)


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
