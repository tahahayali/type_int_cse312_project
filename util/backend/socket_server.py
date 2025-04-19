from flask import Flask, request
from flask_socketio import SocketIO, emit
import random
import eventlet

# Enable eventlet for WebSocket support
eventlet.monkey_patch()

# Flask app and Socket.IO setup
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret'
socketio = SocketIO(app, cors_allowed_origins="*")  # In production, restrict origins

# Dictionary to keep track of connected players
# Format: { sid: { x, y, it } }
players = {}

# Root route (optional API health check or landing page)
@app.route('/')
def index():
    return "SocketIO Server Running"

# Handle new player connections
@socketio.on('connect')
def handle_connect():
    sid = request.sid
    print(f"[+] Connected: {sid}")

    # Generate random spawn coordinates within map bounds
    spawn_x = random.randint(64, 700)
    spawn_y = random.randint(64, 500)

    # First player to join is "it"
    is_it = len(players) == 0

    # Save the player to the global state
    players[sid] = {
        'x': spawn_x,
        'y': spawn_y,
        'it': is_it
    }

    # Send full player list to the newly connected client
    emit('init', {
        'id': sid,
        'players': players
    })

    # Notify all other clients that a new player has joined
    emit('playerJoined', {
        'id': sid,
        'x': spawn_x,
        'y': spawn_y,
        'it': is_it
    }, broadcast=True, include_self=False)

# Handle player movement updates
@socketio.on('move')
def handle_move(data):
    sid = request.sid
    if sid in players:
        # Update player's current position
        players[sid]['x'] = data['x']
        players[sid]['y'] = data['y']

        # Broadcast the new position to all other players
        emit('playerMoved', {
            'id': sid,
            'x': data['x'],
            'y': data['y']
        }, broadcast=True)

# Handle tagging (when the "it" player touches another)
@socketio.on('tag')
def handle_tag(data):
    tagger = request.sid
    target = data.get('id')

    # Tag only works if tagger is "it" and target exists
    if tagger in players and target in players and players[tagger]['it']:
        print(f"[TAG] {tagger} tagged {target}")

        # Transfer "it" status
        players[tagger]['it'] = False
        players[target]['it'] = True

        # Notify all clients of the new "it"
        emit('tagUpdate', {
            'newIt': target,
            'prevIt': tagger
        }, broadcast=True)

# Handle disconnection of a player
@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    print(f"[-] Disconnected: {sid}")

    # Check if the disconnecting player was "it"
    was_it = players.get(sid, {}).get('it', False)

    # Remove player from the global dictionary
    if sid in players:
        del players[sid]

    # Notify other players to remove this player
    emit('playerLeft', {'id': sid}, broadcast=True)

    # If "it" left, assign "it" to a random remaining player
    if was_it and players:
        new_it = random.choice(list(players.keys()))
        players[new_it]['it'] = True
        emit('tagUpdate', {
            'newIt': new_it,
            'prevIt': sid
        }, broadcast=True)

# Run the server on port 5000
if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
