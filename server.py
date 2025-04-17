from flask import Flask, send_from_directory
from flask_socketio import SocketIO

app = Flask(__name__)
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
