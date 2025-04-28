from flask import Flask, request
from flask_socketio import SocketIO, emit
import random, time, eventlet
eventlet.monkey_patch()          # ✱ for the background task

app               = Flask(__name__)
app.config['SECRET_KEY'] = 'secret'
socketio          = SocketIO(app, cors_allowed_origins='*')

MAP_SEED          = random.randint(0, 2**32 - 1)
TAG_COOLDOWN      = 0.20                              # sec

players           = {}   # sid → {x,y,it,name}
it_times          = {}   # sid → {'total', 'started_at'}
became_it_time    = {}   # sid → last-time-became-it


# ───────────────────────── helpers ──────────────────────────
def build_leaderboard():
    """Return a dict that always contains *exactly one* started_at (the red player)."""
    board = {}
    for sid, t in it_times.items():
        board[sid] = {
            'total'      : t.get('total', 0),
            'started_at' : t.get('started_at'),
            'it'         : players.get(sid, {}).get('it', False)
        }
    return board


# ───────────────────── socket events ────────────────────────
@app.route('/')
def index():
    return 'Socket.IO server running'


@socketio.on('connect')
def on_connect():
    sid       = request.sid
    username  = request.args.get('username', f'user-{sid[:4]}')
    spawn_x   = random.randint(64, 700)
    spawn_y   = random.randint(64, 500)
    is_it     = len([p for p in players.values() if p['it']]) == 0

    players[sid] = {'x': spawn_x, 'y': spawn_y, 'it': is_it, 'name': username}
    it_times[sid] = {'total': 0, 'started_at': time.time() if is_it else None}
    if is_it:
        became_it_time[sid] = time.time()

    emit('init',          {'id': sid, 'seed': MAP_SEED,
                           'players': players, 'it_times': build_leaderboard()})
    emit('playerJoined',  {'id': sid, 'x': spawn_x, 'y': spawn_y,
                           'it': is_it, 'name': username},
                           broadcast=True, include_self=False)
    emit('leaderboardUpdate', {'it_times': build_leaderboard()}, broadcast=True)


@socketio.on('move')
def on_move(data):
    sid = request.sid
    if sid in players:
        players[sid]['x'] = data['x']
        players[sid]['y'] = data['y']
        emit('playerMoved', {'id': sid, 'x': data['x'], 'y': data['y']},
             broadcast=True, include_self=False)


@socketio.on('tag')                       # REVERSE TAG  ✓ one handler only
def on_tag(data):
    """Non-IT bumps the red player.  The bumper becomes the new IT."""
    tagger = request.sid
    target = data.get('id')               # ← must currently be IT
    now    = time.time()

    # validation -------------------------------------------------------------
    if tagger not in players or target not in players:
        return
    if not players[target]['it']:                     # must hit someone who is IT
        return
    if target in became_it_time and now - became_it_time[target] < TAG_COOLDOWN:
        return                                        # target still in grace period

    # 1. stop the old-IT timer (TARGET) --------------------------------------
    if it_times[target].get('started_at'):
        it_times[target]['total'] += now - it_times[target]['started_at']
        it_times[target]['started_at'] = None

    # 2. start the new-IT timer (TAGGER) -------------------------------------
    it_times.setdefault(tagger, {'total': 0})
    it_times[tagger]['started_at'] = now

    # 3. flip flags & cooldown ----------------------------------------------
    players[target]['it'] = False
    players[tagger]['it'] = True
    became_it_time[tagger] = now                      # new grace period

    # 4. broadcast -----------------------------------------------------------
    emit('tagUpdate',         {'newIt': tagger, 'prevIt': target}, broadcast=True)
    emit('leaderboardUpdate', {'it_times': build_leaderboard()},     broadcast=True)


@socketio.on('disconnect')
def on_disconnect():
    sid     = request.sid
    if sid not in players:
        return
    was_it  = players[sid]['it']

    # finalise any running timer
    if it_times.get(sid, {}).get('started_at'):
        it_times[sid]['total'] += time.time() - it_times[sid]['started_at']
    players.pop(sid, None)
    it_times.pop(sid, None)
    became_it_time.pop(sid, None)

    emit('playerLeft', {'id': sid}, broadcast=True)

    if was_it and players:                # re-assign IT
        new_it = random.choice(list(players))
        players[new_it]['it'] = True
        it_times.setdefault(new_it, {'total': 0})
        it_times[new_it]['started_at'] = time.time()
        became_it_time[new_it] = time.time()
        emit('tagUpdate', {'newIt': new_it, 'prevIt': sid}, broadcast=True)

    emit('leaderboardUpdate', {'it_times': build_leaderboard()}, broadcast=True)


@socketio.on('getLeaderboard')
def on_get_leaderboard():
    emit('leaderboardUpdate', {'it_times': build_leaderboard()})


# ─── periodic push so the seconds tick in real time ─────────────────────────
def tick_leaderboard():
    while True:
        eventlet.sleep(1)
        if players:
            socketio.emit('leaderboardUpdate', {'it_times': build_leaderboard()})


if __name__ == '__main__':
    socketio.start_background_task(tick_leaderboard)
    socketio.run(app, host='0.0.0.0', port=5000)
