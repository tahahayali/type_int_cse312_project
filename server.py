from flask import Flask, send_from_directory, abort
from flask_socketio import SocketIO
from db.database import users, sessions, login_attempts, stats
from util.backend.logger import log_request, log_raw_http

app = Flask(__name__)
app.after_request(log_request)
app.after_request(log_raw_http)
socketio = SocketIO(app, cors_allowed_origins="*")  # change this to cors_allowed_origins=["https://website_name"] when we're actually in production

@app.post('/register')
def register():
    pass

@app.post('/login')
def login():
    pass

@app.get('/logout')
def logout():
    pass


@app.route('/game')
def game():
    return send_from_directory("public/html", "game.html")


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