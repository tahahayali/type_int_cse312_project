import eventlet
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

socketio = SocketIO(app, cors_allowed_origins="*")  # Allow all origins during dev

from util.backend import socket_server

# Secret Key
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev_secret_key")

# =================== Authentication Routes ===================

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

# =================== Server Start ===================

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=8080)
