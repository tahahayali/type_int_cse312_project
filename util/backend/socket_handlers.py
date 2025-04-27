import random
import time
from flask import request
from flask_socketio import emit
from db.database import update_user_time_as_it, unlock_achievement

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

        # Initialize "it" time to 0 seconds
        it_times[sid] = {"total": 0, "started_at": None}

        # If this player is "it", set their start time
        if is_it:
            it_times[sid]["started_at"] = time.time()

        # Include it_times in the init data
        emit('init', {'id': sid, 'seed': MAP_SEED, 'players': players, 'it_times': it_times})
        emit('playerJoined',
             {'id': sid, 'x': spawn_x, 'y': spawn_y,
              'it': is_it, 'name': username},
             broadcast=True, include_self=False)

        # Send updated leaderboard to all clients
        emit('leaderboardUpdate', {'it_times': it_times}, broadcast=True)
        print(f"Player connected: {sid}, username: {username}, is_it: {is_it}")

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

        # Validate the tag
        if tagger not in players:
            print(f"Tag error: Tagger {tagger} not in players list")
            return

        if target not in players:
            print(f"Tag error: Target {target} not in players list")
            return

        if not players[tagger]['it']:
            print(f"Tag error: Tagger {tagger} is not 'it'")
            return

        print(f"Tag event: {tagger} tagged {target}")

        # Update the time for the previous "it" player
        if tagger in it_times and it_times[tagger].get("started_at"):
            elapsed = time.time() - it_times[tagger]["started_at"]
            it_times[tagger]["total"] += elapsed
            it_times[tagger]["started_at"] = None
            
            # Update total 'it' time in MongoDB for the previous 'it' player
            username_of_tagger = players[tagger]['name']
            update_user_time_as_it(username_of_tagger, it_times[tagger]["total"])

            # Check if the target unlocked 'First Tag' achievement
            username_of_target = players[target]['name']
            unlock_achievement(username_of_target, "first_tag")
            print(f"Updated 'it' time for {tagger}: +{elapsed:.2f}s, total: {it_times[tagger]['total']:.2f}s")

        # Set the new "it" player's start time
        if target not in it_times:
            it_times[target] = {"total": 0, "started_at": time.time()}
        else:
            it_times[target]["started_at"] = time.time()

        # Update player states
        players[tagger]['it'] = False
        players[target]['it'] = True

        print(f"New 'it' player: {target}")

        # Send tag update to all clients
        emit('tagUpdate',
             {'newIt': target, 'prevIt': tagger},
             broadcast=True)

        # Send updated leaderboard
        emit('leaderboardUpdate', {'it_times': it_times}, broadcast=True)

    @socketio.on('disconnect')
    def _dc():
        sid = request.sid

        if sid not in players:
            print(f"Disconnect for unknown player: {sid}")
            return

        was_it = players[sid].get('it', False)
        username = players[sid].get('name', sid[:4])
        print(f"Player disconnected: {sid}, username: {username}, was_it: {was_it}")

        # Update "it" time if the disconnecting player was "it"
        if was_it and sid in it_times and it_times[sid].get("started_at"):
            elapsed = time.time() - it_times[sid]["started_at"]
            it_times[sid]["total"] += elapsed
            it_times[sid]["started_at"] = None
            print(f"Final 'it' time for {sid}: +{elapsed:.2f}s, total: {it_times[sid]['total']:.2f}s")

        # Remove player from both dictionaries
        if sid in players:
            del players[sid]

        # Also remove from it_times to keep leaderboard clean
        if sid in it_times:
            del it_times[sid]

        emit('playerLeft', {'id': sid}, broadcast=True)

        # If they were "it", assign to someone else
        if was_it and players:
            new_it = random.choice(list(players.keys()))
            players[new_it]['it'] = True

            # Set start time for new "it" player
            if new_it not in it_times:
                it_times[new_it] = {"total": 0, "started_at": time.time()}
            else:
                it_times[new_it]["started_at"] = time.time()

            print(f"Assigning new 'it' player: {new_it}")

            emit('tagUpdate',
                 {'newIt': new_it, 'prevIt': sid},
                 broadcast=True)

            # Send updated leaderboard
            emit('leaderboardUpdate', {'it_times': it_times}, broadcast=True)
        else:
            # Always send updated leaderboard after player leaves
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

        active_players = {sid: player for sid, player in players.items()}
        active_it_times = {sid: time_data for sid, time_data in it_times.items() if sid in active_players}

        emit('leaderboardUpdate', {'it_times': active_it_times})