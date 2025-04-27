import random
import time
from flask import request
from flask_socketio import emit

# will be filled from server.py
socketio = None
players = {}
MAP_SEED = random.randint(0, 2 ** 32 - 1)
it_times = {}  # Track how long each player has been "it"


def init_handlers(sock):
    """Call this exactly once from server.py after you create its SocketIO()"""
    global socketio
    socketio = sock

    @socketio.on('connect')
    def _connect():
        sid = request.sid
        username = request.args.get('username', f'user-{sid[:4]}')
        spawn_x = random.randint(64, 700)
        spawn_y = random.randint(64, 500)
        is_it = len(players) == 0

        players[sid] = dict(x=spawn_x, y=spawn_y, it=is_it, name=username)
        it_times[sid] = 0  # Initialize "it" time to 0 seconds

        # If this player is "it", set their start time
        if is_it:
            it_times[sid] = {"total": 0, "started_at": time.time()}

        # Include it_times in the init data
        emit('init', {'id': sid, 'seed': MAP_SEED, 'players': players, 'it_times': it_times})
        emit('playerJoined',
             {'id': sid, 'x': spawn_x, 'y': spawn_y,
              'it': is_it, 'name': username},
             broadcast=True, include_self=False)

        # Send updated leaderboard to all clients
        emit('leaderboardUpdate', {'it_times': it_times}, broadcast=True)

    @socketio.on('move')
    def _move(data):
        sid = request.sid
        if sid in players:
            players[sid]['x'] = data['x']
            players[sid]['y'] = data['y']
            emit('playerMoved', {'id': sid, **data}, broadcast=True)

    @socketio.on('tag')
    def _tag(data):
        tagger = request.sid
        target = data.get('id')
        if tagger in players and target in players and players[tagger]['it']:
            # Update the time for the previous "it" player
            if it_times[tagger].get("started_at"):
                elapsed = time.time() - it_times[tagger]["started_at"]
                it_times[tagger]["total"] += elapsed
                it_times[tagger]["started_at"] = None

            # Set the new "it" player's start time
            if target not in it_times:
                it_times[target] = {"total": 0, "started_at": time.time()}
            else:
                it_times[target]["started_at"] = time.time()

            # Update player states
            players[tagger]['it'] = False
            players[target]['it'] = True

            # Send tag update
            emit('tagUpdate',
                 {'newIt': target, 'prevIt': tagger},
                 broadcast=True)

            # Send updated leaderboard
            emit('leaderboardUpdate', {'it_times': it_times}, broadcast=True)

    @socketio.on('disconnect')
    def _dc():
        sid = request.sid
        was_it = players.get(sid, {}).get('it', False)

        # Update "it" time if the disconnecting player was "it"
        if was_it and sid in it_times and it_times[sid].get("started_at"):
            elapsed = time.time() - it_times[sid]["started_at"]
            it_times[sid]["total"] += elapsed

        if sid in players:
            del players[sid]

        emit('playerLeft', {'id': sid}, broadcast=True)

        if was_it and players:
            new_it = random.choice(list(players.keys()))
            players[new_it]['it'] = True

            # Set start time for new "it" player
            if new_it not in it_times:
                it_times[new_it] = {"total": 0, "started_at": time.time()}
            else:
                it_times[new_it]["started_at"] = time.time()

            emit('tagUpdate',
                 {'newIt': new_it, 'prevIt': sid},
                 broadcast=True)

            # Send updated leaderboard
            emit('leaderboardUpdate', {'it_times': it_times}, broadcast=True)

    # Add a new handler to handle leaderboard requests
    @socketio.on('getLeaderboard')
    def _get_leaderboard():
        # Update the current "it" player's time before sending
        for sid, player in players.items():
            if player['it'] and sid in it_times and it_times[sid].get("started_at"):
                current_elapsed = time.time() - it_times[sid]["started_at"]
                current_total = it_times[sid]["total"] + current_elapsed
                # Just calculate it but don't update the stored value
                it_times[sid]["current_total"] = current_total

        emit('leaderboardUpdate', {'it_times': it_times})