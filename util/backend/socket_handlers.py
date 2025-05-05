'''
This is 1st try for socket_handlers.py
'''

# import random
# import time
# from flask import request
# from flask_socketio import emit
# from db.database import update_user_time_as_it, unlock_achievement
#
# # will be filled from server.py
# socketio = None
# players = {}
# MAP_SEED = random.randint(0, 2 ** 32 - 1)
# it_times = {}  # Track how long each player has been "it"
# became_it_time = {}  # Track when each player became "it" for cooldown
# TAG_COOLDOWN = 0.2  # 0.2 seconds cooldown
#
#
# def init_handlers(sock):
#     """Call this exactly once from server.py after you create its SocketIO()"""
#     global socketio
#     socketio = sock
#
#     @socketio.on('connect')
#     def _connect():
#         sid = request.sid
#         username = request.args.get('username', f'user-{sid[:4]}')
#         spawn_x = random.randint(64, 700)
#         spawn_y = random.randint(64, 500)
#         is_it = len(players) == 0
#
#         players[sid] = dict(x=spawn_x, y=spawn_y, it=is_it, name=username)
#
#         # Initialize "it" time to 0 seconds
#         it_times[sid] = {"total": 0, "started_at": None}
#
#         # If this player is "it", set their start time
#         if is_it:
#             it_times[sid]["started_at"] = time.time()
#             became_it_time[sid] = time.time()  # Initialize cooldown time
#
#         # Include it_times in the init data
#         emit('init', {'id': sid, 'seed': MAP_SEED, 'players': players, 'it_times': it_times})
#         emit('playerJoined',
#              {'id': sid, 'x': spawn_x, 'y': spawn_y,
#               'it': is_it, 'name': username},
#              broadcast=True, include_self=False)
#
#         # Send updated leaderboard to all clients
#         emit('leaderboardUpdate', {'it_times': it_times}, broadcast=True)
#         print(f"Player connected: {sid}, username: {username}, is_it: {is_it}")
'''
This is 2nd try for socket_handlers.py

'''
# import random, time
# from flask import request
# from flask_socketio import emit
# from db.database import sessions, update_user_time_as_it, unlock_achievement
# import bcrypt
# import jwt as pyjwt
# import os
#
# # These get set by init_handlers:
# socketio = None
# players = {}
# it_times = {}
# became_it_time = {}
# TAG_COOLDOWN = 0.2
# MAP_SEED = random.randint(0, 2**32 - 1)
# SECRET_KEY = os.environ.get("SECRET_KEY", "dev_secret_key")
#
# def init_handlers(sock):
#     global socketio
#     socketio = sock
#
#     @socketio.on('connect')
#     def _connect():
#         sid = request.sid
#
#         # Authenticate via the same JWT cookie
#         token = request.cookies.get('auth_token')
#         if not token:
#             return False  # reject
#         try:
#             payload = pyjwt.decode(token, SECRET_KEY, algorithms=['HS256'])
#             username = payload['username']
#         except Exception:
#             return False
#
#         # **Single-session enforcement**
#         sess = sessions.find_one({"username": username})
#         if sess and sess.get("socket_id") and sess["socket_id"] != sid:
#             # force‐disconnect the old socket
#             try:
#                 socketio.server.disconnect(sess["socket_id"])
#             except Exception:
#                 pass
#
#         # update this session doc with our new socket id
#         sessions.update_one(
#             {"username": username},
#             {"$set": {"socket_id": sid}}
#         )
#
#         # now the usual game‐join logic…
#         spawn_x = random.randint(64, 700)
#         spawn_y = random.randint(64, 500)
#         is_it = len(players) == 0
#
#         players[sid] = {"x": spawn_x, "y": spawn_y, "it": is_it, "name": username}
#         it_times[sid] = {"total": 0, "started_at": time.time() if is_it else None}
#         if is_it:
#             became_it_time[sid] = time.time()
#
#         emit('init', {
#             'id':       sid,
#             'seed':     MAP_SEED,
#             'players':  players,
#             'it_times': it_times
#         })
#         emit('playerJoined', {
#             'id': sid, 'x': spawn_x, 'y': spawn_y,
#             'it': is_it, 'name': username
#         }, broadcast=True, include_self=False)
#         emit('leaderboardUpdate', {'it_times': it_times}, broadcast=True)
#
#     # … rest of your move, tag, disconnect, etc. unchanged …
#
#     @socketio.on('move')
#     def _move(data):
#         sid = request.sid
#         if sid in players:
#             players[sid]['x'] = data['x']
#             players[sid]['y'] = data['y']
#             emit('playerMoved', {'id': sid, **data}, broadcast=True)
#
#     @socketio.on('tag')
#     def _tag(data):
#         tagger = request.sid
#         target = data.get('id')
#         current_time = time.time()
#
#         # Validate the tag
#         if tagger not in players:
#             print(f"Tag error: Tagger {tagger} not in players list")
#             return
#
#         if target not in players:
#             print(f"Tag error: Target {target} not in players list")
#             return
#
#         if not players[tagger]['it']:
#             print(f"Tag error: Tagger {tagger} is not 'it'")
#             return
#
#         # Check if the tagger just became "it" (on cooldown)
#         if tagger in became_it_time and (current_time - became_it_time[tagger]) < TAG_COOLDOWN:
#             print(f"Tag error: Tagger {tagger} is on cooldown (recently became 'it')")
#             return
#
#         print(f"Tag event: {tagger} tagged {target}")
#
#         # Update the time for the previous "it" player
#         if tagger in it_times and it_times[tagger].get("started_at"):
#             elapsed = time.time() - it_times[tagger]["started_at"]
#             it_times[tagger]["total"] += elapsed
#             it_times[tagger]["started_at"] = None
#
#             # Update total 'it' time in MongoDB for the previous 'it' player
#             username_of_tagger = players[tagger]['name']
#             update_user_time_as_it(username_of_tagger, it_times[tagger]["total"])
#
#             # Check if the target unlocked 'First Tag' achievement
#             username_of_target = players[target]['name']
#             unlock_achievement(username_of_target, "first_tag")
#             print(f"Updated 'it' time for {tagger}: +{elapsed:.2f}s, total: {it_times[tagger]['total']:.2f}s")
#
#         # Set the new "it" player's start time
#         if target not in it_times:
#             it_times[target] = {"total": 0, "started_at": time.time()}
#         else:
#             it_times[target]["started_at"] = time.time()
#
#         # Update player states
#         players[tagger]['it'] = False
#         players[target]['it'] = True
#
#         # Record when the target became "it" for cooldown
#         became_it_time[target] = current_time
#
#         print(f"New 'it' player: {target}")
#
#         # Send tag update to all clients
#         emit('tagUpdate',
#              {'newIt': target, 'prevIt': tagger},
#              broadcast=True)
#
#         # Send updated leaderboard
#         emit('leaderboardUpdate', {'it_times': it_times}, broadcast=True)
#
#     @socketio.on('disconnect')
#     def _dc():
#         sid = request.sid
#
#         if sid not in players:
#             print(f"Disconnect for unknown player: {sid}")
#             return
#
#         # Clean up cooldown tracking when player disconnects
#         if sid in became_it_time:
#             del became_it_time[sid]
#
#         was_it = players[sid].get('it', False)
#         username = players[sid].get('name', sid[:4])
#         print(f"Player disconnected: {sid}, username: {username}, was_it: {was_it}")
#
#         # Update "it" time if the disconnecting player was "it"
#         if was_it and sid in it_times and it_times[sid].get("started_at"):
#             elapsed = time.time() - it_times[sid]["started_at"]
#             it_times[sid]["total"] += elapsed
#             it_times[sid]["started_at"] = None
#             print(f"Final 'it' time for {sid}: +{elapsed:.2f}s, total: {it_times[sid]['total']:.2f}s")
#
#         # Remove player from both dictionaries
#         if sid in players:
#             del players[sid]
#
#         # Also remove from it_times to keep leaderboard clean
#         if sid in it_times:
#             del it_times[sid]
#
#         emit('playerLeft', {'id': sid}, broadcast=True)
#
#         # If they were "it", assign to someone else
#         if was_it and players:
#             new_it = random.choice(list(players.keys()))
#             players[new_it]['it'] = True
#
#             # Set start time for new "it" player
#             if new_it not in it_times:
#                 it_times[new_it] = {"total": 0, "started_at": time.time()}
#             else:
#                 it_times[new_it]["started_at"] = time.time()
#
#             # Set cooldown for the new "it" player
#             became_it_time[new_it] = time.time()
#
#             print(f"Assigning new 'it' player: {new_it}")
#
#             emit('tagUpdate',
#                  {'newIt': new_it, 'prevIt': sid},
#                  broadcast=True)
#
#             # Send updated leaderboard
#             emit('leaderboardUpdate', {'it_times': it_times}, broadcast=True)
#         else:
#             # Always send updated leaderboard after player leaves
#             emit('leaderboardUpdate', {'it_times': it_times}, broadcast=True)
#
#     # Add a new handler to handle leaderboard requests
#     @socketio.on('getLeaderboard')
#     def _get_leaderboard():
#         # Update the current "it" player's time before sending
#         for sid, player in players.items():
#             if player['it'] and sid in it_times and it_times[sid].get("started_at"):
#                 current_elapsed = time.time() - it_times[sid]["started_at"]
#                 current_total = it_times[sid]["total"] + current_elapsed
#                 # Just calculate it but don't update the stored value
#                 it_times[sid]["current_total"] = current_total
#
#         active_players = {sid: player for sid, player in players.items()}
#         active_it_times = {sid: time_data for sid, time_data in it_times.items() if sid in active_players}
#
#         emit('leaderboardUpdate', {'it_times': active_it_times})
#
import random, time
from flask import request
from flask_socketio import emit
from db.database import sessions, update_user_time_as_it, unlock_achievement
import jwt as pyjwt
import os

# Globals set by init_handlers
socketio = None
players = {}
it_times = {}
became_it_time = {}
TAG_COOLDOWN = 0.2
MAP_SEED = random.randint(0, 2**32 - 1)
SECRET_KEY = os.environ.get("SECRET_KEY", "dev_secret_key")


def build_enriched_it_times():
    enriched = {}
    for sid, times in it_times.items():
        enriched[sid] = {
            'total': times.get('total', 0),
            'started_at': times.get('started_at'),
            'it': players.get(sid, {}).get('it', False)
        }
        print("Sending leaderboard:", enriched)
    return enriched


def init_handlers(sock):
    """Register all Socket.IO event handlers."""
    global socketio
    socketio = sock

    @socketio.on('connect')
    def _connect():
        sid = request.sid
        # Validate Auth Token
        token = request.cookies.get('auth_token')
        if not token:
            return False  # reject unauthorized
        try:
            payload = pyjwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            username = payload['username']
        except Exception:
            return False

        # Single-session: disconnect old socket
        sess = sessions.find_one({"username": username})
        old_sid = sess.get('socket_id') if sess else None
        if old_sid and old_sid != sid:
            try:
                socketio.server.disconnect(old_sid)
            except Exception:
                pass
        sessions.update_one({"username": username}, {"$set": {"socket_id": sid}})

        # Choose spawn location
        spawn_x = random.randint(64, 700)
        spawn_y = random.randint(64, 500)
        is_it = len([p for p in players.values() if p['it']]) == 0

        # Register new player
        players[sid] = {"x": spawn_x, "y": spawn_y, "it": is_it, "name": username}
        it_times[sid] = {"total": 0, "started_at": time.time() if is_it else None}
        if is_it:
            became_it_time[sid] = time.time()

        # Send initial state
        emit('init', {'id': sid, 'seed': MAP_SEED, 'players': players, 'it_times': it_times})
        emit('playerJoined', {'id': sid, 'x': spawn_x, 'y': spawn_y, 'it': is_it, 'name': username}, broadcast=True, include_self=False)

        # Send updated leaderboard
        emit('leaderboardUpdate', {'it_times': build_enriched_it_times()}, broadcast=True)

        print(f"Player connected: {sid} ({username}), it={is_it}")

    # @socketio.on('tag')
    # def _tag(data):
    #     tagger = request.sid
    #     target = data.get('id')
    #     now = time.time()
    #
    #     if tagger not in players or target not in players:
    #         return
    #     if not players[target]['it']:
    #         return
    #     if target in became_it_time and now - became_it_time[target] < TAG_COOLDOWN:
    #         return
    #
    #     # stop TARGET’s timer
    #     if it_times[target].get('started_at'):
    #         it_times[target]['total'] += now - it_times[target]['started_at']
    #         it_times[target]['started_at'] = None
    #
    #     # start TAGGER’s timer
    #     it_times.setdefault(tagger, {'total': 0})
    #     it_times[tagger]['started_at'] = now
    #
    #     players[target]['it'] = False
    #     players[tagger]['it'] = True
    #     became_it_time[tagger] = now
    #
    #     emit('tagUpdate', {'newIt': tagger, 'prevIt': target}, broadcast=True)
    #     emit('leaderboardUpdate', {'it_times': build_enriched_it_times()}, broadcast=True)
    @socketio.on('tag')
    def _tag(data):
        tagger = request.sid
        target = data.get('id')
        now = time.time()

        # ─────────── Validation ───────────
        # Both sides must be connected
        if tagger not in players or target not in players:
            return

        # Only bump the current “it” player
        if not players[target]['it']:
            return

        # Enforce cooldown on newly-tagged
        if target in became_it_time and now - became_it_time[target] < TAG_COOLDOWN:
            return

        # ───────── Stop TARGET’s timer ─────────
        if it_times[target].get('started_at'):
            elapsed = now - it_times[target]['started_at']
            it_times[target]['total'] += elapsed
            it_times[target]['started_at'] = None

            # ─────── record in Mongo ───────
            from db.database import increment_user_tags, increment_user_time
            # tagger gains one tag
            increment_user_tags(players[tagger]['name'], 1)
            # add elapsed “it” time for the previous it‐player
            increment_user_time(players[target]['name'], elapsed)

        # ───────── Start TAGGER’s timer ─────────
        it_times.setdefault(tagger, {'total': 0})
        it_times[tagger]['started_at'] = now

        # Swap “it” flags
        players[target]['it'] = False
        players[tagger]['it'] = True
        became_it_time[tagger] = now

        # ───────── Broadcast updates ─────────
        emit('tagUpdate', {'newIt': tagger, 'prevIt': target}, broadcast=True)
        emit('leaderboardUpdate', {'it_times': build_enriched_it_times()}, broadcast=True)

    @socketio.on('move')
    def _move(data):
        sid = request.sid
        if sid in players:
            players[sid]['x'] = data['x']
            players[sid]['y'] = data['y']
            emit('playerMoved', {'id': sid, 'x': data['x'], 'y': data['y']}, broadcast=True)

    # @socketio.on('tag')
    # def _tag(data):
    #     tagger = request.sid
    #     target = data.get('id')
    #     now = time.time()
    #
    #     # Only allow tag if target is current 'it'
    #     if target not in players or not players[target]['it']:
    #         return
    #     if target in became_it_time and now - became_it_time[target] < TAG_COOLDOWN:
    #         return
    #
    #     # Swap roles
    #     players[target]['it'] = False
    #     players[tagger]['it'] = True
    #
    #     # Update timing for old 'it'
    #     start = it_times[target].get('started_at')
    #     if start:
    #         elapsed = now - start
    #         it_times[target]['total'] += elapsed
    #         update_user_time_as_it(players[target]['name'], it_times[target]['total'])
    #
    #     # Start timing for new 'it'
    #     it_times[tagger] = it_times.get(tagger, {'total': 0})
    #     it_times[tagger]['started_at'] = now
    #     became_it_time[tagger] = now
    #
    #     emit('tagUpdate', {'newIt': tagger, 'prevIt': target}, broadcast=True)
    #     emit('leaderboardUpdate', {'it_times': build_enriched_it_times()}, broadcast=True)
    #     print(f"Tag: {tagger} tagged {target}")

    @socketio.on('disconnect')
    def _dc():
        sid = request.sid
        if sid not in players:
            return
        was_it = players[sid]['it']

        # Finalize timing
        start = it_times[sid].get('started_at')
        if start:
            elapsed = time.time() - start
            it_times[sid]['total'] += elapsed
            update_user_time_as_it(players[sid]['name'], it_times[sid]['total'])

        # Clean up
        players.pop(sid, None)
        it_times.pop(sid, None)
        became_it_time.pop(sid, None)

        emit('playerLeft', {'id': sid}, broadcast=True)

        # Reassign 'it' if needed
        if was_it and players:
            new_it = random.choice(list(players.keys()))
            players[new_it]['it'] = True
            it_times[new_it] = it_times.get(new_it, {'total': 0})
            it_times[new_it]['started_at'] = time.time()
            became_it_time[new_it] = time.time()
            emit('tagUpdate', {'newIt': new_it, 'prevIt': sid}, broadcast=True)

        emit('leaderboardUpdate', {'it_times': build_enriched_it_times()}, broadcast=True)

    @socketio.on('getLeaderboard')
    def _get_leaderboard():
        # Refresh current 'it' times
        for sid, p in players.items():
            if p['it'] and sid in it_times and it_times[sid].get('started_at'):
                it_times[sid]['current_total'] = it_times[sid]['total'] + (time.time() - it_times[sid]['started_at'])
        emit('leaderboardUpdate', {'it_times': build_enriched_it_times()}, broadcast=True)