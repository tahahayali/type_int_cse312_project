
import random, time
from typing import Optional

from flask import request
from flask_socketio import emit
from db.database import sessions, update_user_time_as_it, unlock_achievement, update_leaderboard
import jwt as pyjwt
import os


# Globals set by init_handlers
socketio = None
players = {}
it_times = {}
became_it_time = {}
TAG_COOLDOWN = 0.2
MAP_SEED = random.randint(0, 2**32 - 1)
from util.backend.map_generator import generate_blocked_tiles

BLOCKED_TILES, FREE_TILES = generate_blocked_tiles(MAP_SEED)
free_spawn_pool = FREE_TILES.copy()
random.shuffle(free_spawn_pool)


SECRET_KEY = os.environ.get("SECRET_KEY", "dev_secret_key")
ALLOWED_EXTENSIONS_ON_DISK = ("png", "jpg", "jpeg")

def get_free_spawn():
    """Return pixel co‑ordinates on a walkable tile (48 px grid)."""
    tile_size = 16 * 3          # same as client
    if free_spawn_pool:
        tx, ty = free_spawn_pool.pop()
    else:                       # safety fallback – linear scan
        for tx in range(1, 58):
            for ty in range(1, 38):
                if (tx, ty) not in BLOCKED_TILES:
                    break
    return tx * tile_size, ty * tile_size




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

def get_avatar_url(username: str) -> Optional[str]:
    """Return '/static/avatars/<file>' or None if no avatar exists."""
    for ext in ALLOWED_EXTENSIONS_ON_DISK:
        candidate = f"static/avatars/{username}.{ext}"
        if os.path.exists(candidate):
            return f"/{candidate}"        # leading slash for URL
    return None

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
            avatar_url = get_avatar_url(username)

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
        spawn_x, spawn_y = get_free_spawn()

        is_it = len([p for p in players.values() if p['it']]) == 0

        # Register new player
        players[sid] = {"x": spawn_x, "y": spawn_y, "it": is_it, "name": username, "avatar":avatar_url}
        it_times[sid] = {"total": 0, "started_at": time.time() if is_it else None}
        if is_it:
            became_it_time[sid] = time.time()

        # Send initial state
        emit('init', {'id': sid, 'seed': MAP_SEED, 'players': players, 'it_times': it_times})
        emit('playerJoined', {'id': sid, 'x': spawn_x, 'y': spawn_y, 'it': is_it, 'name': username, 'avatar':avatar_url}, broadcast=True, include_self=False)

        # Send updated leaderboard
        emit('leaderboardUpdate', {'it_times': build_enriched_it_times()}, broadcast=True)

        print(f"Player connected: {sid} ({username}), it={is_it}")

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
            # update leaderboard if this was a new personal best
            update_leaderboard(players[target]['name'], int(it_times[target]['total']))


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
            update_leaderboard(players[sid]['name'], int(it_times[sid]['total']))

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