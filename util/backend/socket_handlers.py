import random, time
from typing import Optional, List

from flask import request
from flask_socketio import emit
from db.database import sessions, update_user_time_as_it, unlock_achievement, update_leaderboard, increment_user_tags, \
    increment_user_time, get_user_achievements
import jwt as pyjwt
import os

# Globals set by init_handlers
socketio = None
players = {}
it_times = {}
became_it_time = {}
TAG_COOLDOWN = 0.2
MAP_SEED = random.randint(0, 2 ** 32 - 1)
SECRET_KEY = os.environ.get("SECRET_KEY", "dev_secret_key")
ALLOWED_EXTENSIONS_ON_DISK = ("png", "jpg", "jpeg")


def build_enriched_it_times():
    enriched = {}
    for sid, times in it_times.items():
        enriched[sid] = {
            'total': times.get('total', 0),
            'started_at': times.get('started_at'),
            'it': players.get(sid, {}).get('it', False)
        }
    return enriched


def get_avatar_url(username: str) -> Optional[str]:
    """Return '/static/avatars/<file>' or None if no avatar exists."""
    for ext in ALLOWED_EXTENSIONS_ON_DISK:
        candidate = f"static/avatars/{username}.{ext}"
        if os.path.exists(candidate):
            return f"/{candidate}"  # leading slash for URL
    return None


def emit_achievement(achievement_type, room_sid):
    """Helper to emit achievement with proper name and description."""
    print(f"Emitting achievement {achievement_type} to {room_sid}")
    if achievement_type == "first_tag":
        emit('achievementUnlocked', {
            'achievement': 'first_tag',
            'name': 'First Tag',
            'description': 'Tag another player for the first time'
        }, room=room_sid)
    elif achievement_type == "survivor_10min":
        emit('achievementUnlocked', {
            'achievement': 'survivor_10min',
            'name': '10-Minute Survivor',
            'description': 'Stay as \'it\' for 10 minutes total'
        }, room=room_sid)
    elif achievement_type == "survivor_1hour":
        emit('achievementUnlocked', {
            'achievement': 'survivor_1hour',
            'name': 'Ultimate Survivor',
            'description': 'Stay as \'it\' for 1 hour total'
        }, room=room_sid)


def check_time_based_achievements(username, sid, current_time):
    """
    Check if a player has earned any time-based achievements based on current time.
    This is called during regular leaderboard updates to catch achievements in real-time.
    """
    from db.database import users

    # Get user data
    user = users.find_one({"username": username})
    if not user:
        return []

    # Calculate current total time including ongoing session
    base_time = user.get("totalTimeIt", 0)
    total_time = base_time + current_time

    # Check for time thresholds and unlock if needed
    unlocked = []

    # Check 10-minute achievement
    if total_time >= 600 and base_time < 600:  # Just crossed 10 minutes threshold
        print(f"Real-time 10min achievement check: {username} has {total_time} seconds")
        if unlock_achievement(username, "survivor_10min"):
            unlocked.append("survivor_10min")

    # Check 1-hour achievement
    if total_time >= 3600 and base_time < 3600:  # Just crossed 1 hour threshold
        print(f"Real-time 1hour achievement check: {username} has {total_time} seconds")
        if unlock_achievement(username, "survivor_1hour"):
            unlocked.append("survivor_1hour")

    return unlocked


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
        sessions.update_one({"username": username}, {"$set": {"socket_id": sid}}, upsert=True)

        # Choose spawn location
        spawn_x = random.randint(64, 700)
        spawn_y = random.randint(64, 500)
        is_it = len([p for p in players.values() if p['it']]) == 0

        # Register new player
        players[sid] = {"x": spawn_x, "y": spawn_y, "it": is_it, "name": username, "avatar": avatar_url}
        it_times[sid] = {"total": 0, "started_at": time.time() if is_it else None}
        if is_it:
            became_it_time[sid] = time.time()

        # Send initial state
        emit('init', {'id': sid, 'seed': MAP_SEED, 'players': players, 'it_times': it_times})
        emit('playerJoined',
             {'id': sid, 'x': spawn_x, 'y': spawn_y, 'it': is_it, 'name': username, 'avatar': avatar_url},
             broadcast=True, include_self=False)

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

        # Only bump the current "it" player
        if not players[target]['it']:
            return

        # Enforce cooldown on newly-tagged
        if target in became_it_time and now - became_it_time[target] < TAG_COOLDOWN:
            return

        # ───────── Stop TARGET's timer ─────────
        if it_times[target].get('started_at'):
            elapsed = now - it_times[target]['started_at']
            it_times[target]['total'] += elapsed
            it_times[target]['started_at'] = None

            # ─────── record in Mongo ───────
            # tagger gains one tag
            tagger_username = players[tagger]['name']
            target_username = players[target]['name']

            # Check for first tag achievement
            if unlock_achievement(tagger_username, "first_tag"):
                print(f"First tag achievement unlocked for {tagger_username}")
                emit_achievement("first_tag", tagger)

            increment_user_tags(tagger_username, 1)

            # Add elapsed "it" time for the previous it-player and check for time achievements
            try:
                new_achievements = increment_user_time(target_username, elapsed) or []
                print(f"Tag event: New achievements for {target_username}: {new_achievements}")

                # If any new achievements were unlocked, emit events
                for achievement in new_achievements:
                    print(f"Emitting {achievement} achievement to {target}")
                    emit_achievement(achievement, target)

                # update leaderboard if this was a new personal best
                update_leaderboard(target_username, int(it_times[target]['total']))
            except Exception as e:
                print(f"Error processing achievements in tag event: {e}")

        # ───────── Start TAGGER's timer ─────────
        it_times.setdefault(tagger, {'total': 0})
        it_times[tagger]['started_at'] = now

        # Swap "it" flags
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
        player_username = players[sid]['name']

        # Finalize timing
        try:
            if sid in it_times and it_times[sid].get('started_at'):
                elapsed = time.time() - it_times[sid]['started_at']
                it_times[sid]['total'] += elapsed

                # Update time in database and check for achievements
                update_user_time_as_it(player_username, it_times[sid]['total'])
                new_achievements = increment_user_time(player_username, elapsed) or []
                print(f"Disconnect - New achievements for {player_username}: {new_achievements}")

                # If any new achievements were unlocked, emit events
                for achievement in new_achievements:
                    print(f"Disconnect - Emitting {achievement} to {sid}")
                    emit_achievement(achievement, sid)

                update_leaderboard(player_username, int(it_times[sid]['total']))
        except Exception as e:
            print(f"Error finalizing time on disconnect: {e}")

        # Clean up
        players.pop(sid, None)
        it_times.pop(sid, None)
        became_it_time.pop(sid, None)

        emit('playerLeft', {'id': sid}, broadcast=True)

        # Reassign 'it' if needed
        if was_it and players:
            player_keys = list(players.keys())
            if player_keys:  # Make sure there are still players left
                new_it = random.choice(player_keys)
                players[new_it]['it'] = True
                it_times.setdefault(new_it, {'total': 0})
                it_times[new_it]['started_at'] = time.time()
                became_it_time[new_it] = time.time()
                emit('tagUpdate', {'newIt': new_it, 'prevIt': sid}, broadcast=True)

        emit('leaderboardUpdate', {'it_times': build_enriched_it_times()}, broadcast=True)

    @socketio.on('getLeaderboard')
    def _get_leaderboard():
        # Check for time-based achievements for all active players
        for sid, player in players.items():
            if player.get('it', False) and sid in it_times and it_times[sid].get('started_at'):
                username = player['name']
                current_time = time.time() - it_times[sid]['started_at']

                try:
                    # Check if any new achievements should be unlocked based on current time
                    new_achievements = check_time_based_achievements(username, sid, current_time)

                    # Emit notifications for any new achievements
                    for achievement in new_achievements:
                        print(f"Leaderboard update - Emitting {achievement} achievement to {sid}")
                        emit_achievement(achievement, sid)
                except Exception as e:
                    print(f"Error checking achievements during leaderboard update: {e}")

        # Send the updated leaderboard
        emit('leaderboardUpdate', {'it_times': build_enriched_it_times()}, broadcast=True)

    @socketio.on('getAchievements')
    def _get_achievements():
        """Handle requests for a user's achievements"""
        sid = request.sid
        if sid not in players:
            return

        username = players[sid]['name']
        achievements = get_user_achievements(username)
        print(f"Fetched achievements for {username}: {achievements}")

        # Look for any existing achievements to potentially show notifications
        if achievements:
            for achievement_type, data in achievements.items():
                if data and data.get('unlocked'):
                    # Only notify for achievements unlocked in the last minute
                    # This helps if they reconnect shortly after earning an achievement
                    if 'unlockDate' in data and data['unlockDate'] and (
                            time.time() - data['unlockDate'].timestamp() < 60):
                        emit_achievement(achievement_type, sid)

        # Send the achievements data
        emit('achievementsUpdate', {'achievements': achievements})