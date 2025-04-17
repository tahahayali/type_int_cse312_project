"""
Set up Flask-SocketIO for real-time movement
Design message format for movement, state updates (e.g., {"x": ..., "y": ..., "id": ..., "isIt": true})
Maintain server-side game state: player positions, who's "it", time tracking
Implement timer to track how long each player is “it”
Broadcast updates to all clients

"""

from flask import Flask
from flask_socketio import SocketIO


app = Flask(__name__) # What does this do?
socketio = SocketIO(app)

# PSEDOCODE, I'm not sure how flask works
# get upgrade request to switch to websockets? would we even get this
# where would we get the coordinates for the user? Would the frontend send this information?
# I think so, as that's what we did in the previous project
# To track how long user is it, what would we do? Would we start a timer when we get our first isIt = true?
# then end the timer when isIt = false?
# official state updates can look like: {'player updates' : {"x": x_coor, "y": y_coor, "username": 'xyz', "isIt": t/f}}
# Should we get two different messages, one for normal players, one for the player that is it?
# For the one that is it the update can look like: {'it updates' : {"x": x_coor, "y": y_coor, "username": 'xyz', "isIt": t/f, 'time_it': 00:00}}