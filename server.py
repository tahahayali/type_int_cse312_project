import eventlet
eventlet.monkey_patch()

import os
from flask import Flask, send_from_directory, abort, g, jsonify
from flask_socketio import SocketIO
# from db.database import users, sessions, login_attempts, stats
from util.backend.logger import log_request, log_raw_http
# For authentication
from util.backend.authentication.auth import register, login, logout, token_required

# For avatar uploads
from util.backend.upload.avatar import upload_avatar

app = Flask(__name__)
app.after_request(log_request)
app.after_request(log_raw_http)
socketio = SocketIO(app, cors_allowed_origins="*")  # change this to cors_allowed_origins=["https://website_name"] when we're actually in production
from util.backend import socket_server

# For authentication.
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev_secret_key")

# app.post("/register")(register)
# app.post("/login")(login)
# app.get("/logout")(logout)



@app.post('/register')
def register_route():
    return register()

@app.post('/login')
def login_route():
    return login()

@app.get('/logout')
def logout_route():
    return logout()


@app.route('/game')
def game():
    return send_from_directory("public/html", "game.html")

@app.post("/upload_avatar")
def avatar_upload_route():
    return upload_avatar()

@app.route('/static/avatars/<filename>')
def serve_avatar(filename):
    return send_from_directory('static/avatars', filename)


@app.route('/api/current-user')
@token_required
def current_user():
    """Return information about the currently logged-in user"""
    return jsonify({"username": g.username})
@app.route('/')
def index():
    return send_from_directory("public/html", "home_page.html")


@app.route("/<path:path>")
def serve_static(path):
    try:
        return send_from_directory("public", path)
    except:
        return abort(404)

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=8080)