from flask import Flask, send_from_directory
from flask_socketio import SocketIO
from db.database import users, sessions, login_attempts, stats
from util.backend.logger import log_request, log_raw_http

app = Flask(__name__)
app.after_request(log_request)
app.after_request(log_raw_http)
socketio = SocketIO(app, cors_allowed_origins="*")  # change this to cors_allowed_origins=["https://website_name"] when we're actually in production

@app.route('/api/tag')
def start_tag():
    pass

@app.route('/')
def index():
    return send_from_directory("public/html", "home_page.html")


@app.route("/<path:path>")
def serve_static(path):
    return send_from_directory("public", path)

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=8080)