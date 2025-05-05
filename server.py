import eventlet
from db.database import get_leaderboard, get_aggregated_leaderboard, get_user_achievements
eventlet.monkey_patch()

import os
from flask import Flask, send_from_directory, abort, g, jsonify
from flask_socketio import SocketIO
# from db.database import users, sessions, login_attempts, stats
from util.backend.logger import (
    log_request,
    log_raw_http,
    register_error_handlers
)
from util.backend.authentication.auth import register, login, logout, token_required
from util.backend.upload.avatar import upload_avatar

app = Flask(__name__)

register_error_handlers(app)

app.after_request(log_request)
app.after_request(log_raw_http)

#socketio = SocketIO(app, cors_allowed_origins="*")  # Allow all origins during dev
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")




# --- add these two lines ---
from util.backend.socket_handlers import init_handlers
init_handlers(socketio)

from util.backend import socket_server

# Secret Key
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev_secret_key")



from db.database import users

# =================== Authentication Routes ===================


# Register a new user
@app.route('/api/stats/<username>')
@token_required
def get_stats(username):
    """Return totalTags, totalTimeIt, longestStreak for a given user."""
    doc = users.find_one(
        {"username": username},
        {"_id": 0, "username": 1, "totalTags": 1, "totalTimeIt": 1, "longestStreak": 1}
    )
    if not doc:
        return jsonify(error="User not found"), 404
    return jsonify(doc), 200


@app.route('/api/leaderboard')
def get_leaderboard():
    """
    Aggregated leaderboard (Mongo pipeline):
    - Includes totalTags, totalTimeIt, tagsPerMinute
    - Sorted by least totalTimeIt
    """
    board = get_aggregated_leaderboard(limit=50)
    return jsonify(board), 200

@app.route('/api/achievements')
@token_required
def get_achievements():
    """
    Get achievements for the current user
    """
    username = g.username
    achievements = get_user_achievements(username)
    return jsonify(achievements), 200


#_____________________________________________________________________


@app.post('/register')
def register_route():
    return register()

@app.post('/login')
def login_route():
    return login()

@app.get('/logout')
def logout_route():
    return logout()

# =================== Game Routes ===================

@app.route('/game')
def game():
    return send_from_directory('public/html', 'game.html')

@app.route('/')
def home():
    return send_from_directory('public/html', 'home_page.html')

@app.route('/achievements')
def achievements_page():
    return send_from_directory('public/html', 'achievements.html')

@app.route('/upload_avatar_page')
def upload_avatar_page():
    return send_from_directory('public/html', 'upload_avatar.html')

@app.post('/upload_avatar')
def avatar_upload_route():
    return upload_avatar()

@app.route('/static/avatars/<filename>')
def serve_avatar(filename):
    return send_from_directory('static/avatars', filename)

@app.route('/api/current-user')
@token_required
def current_user():
    return jsonify({"username": g.username})

# ---------- Extra pages ----------
@app.route('/leaderboard_page')
def global_leaderboard_page():
    return send_from_directory('public/html', 'leaderboard.html')

@app.route('/stats_page')
def stats_page():
    return send_from_directory('public/html', 'stats.html')


# =================== Static File Routes ===================

# Serve JS, CSS, assets (tilesets, etc.)
@app.route('/assets/<path:filename>')
def serve_assets(filename):
    return send_from_directory('public/assets', filename)

@app.route('/js/<path:filename>')
def serve_js(filename):
    return send_from_directory('public/js', filename)

@app.route('/css/<path:filename>')
def serve_css(filename):
    return send_from_directory('public/css', filename)

@app.route('/favicon.ico')
def favicon():
    # Optional: fix annoying browser favicon request
    return send_from_directory('public', 'favicon.ico')

# Generic fallback if no route matches
@app.route('/<path:path>')
def fallback(path):
    try:
        return send_from_directory('public', path)
    except:
        return abort(404)


@app.route("/leaderboard", methods=["GET"])
def longest_streak_leaderboard():
    leaderboard_data = get_leaderboard()
    return jsonify(leaderboard_data)
# =================== Server Start ===================

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=8080)
# ---------------------------
