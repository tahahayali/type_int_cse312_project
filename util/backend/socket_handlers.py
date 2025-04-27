import random
from flask import request
from flask_socketio import emit

# will be filled from server.py
socketio = None
players  = {}
MAP_SEED = random.randint(0, 2**32 - 1)


def init_handlers(sock):
    """Call this exactly once from server.py after you create its SocketIO()"""
    global socketio
    socketio = sock

    @socketio.on('connect')
    def _connect():
        sid       = request.sid
        username  = request.args.get('username', f'user-{sid[:4]}')
        spawn_x   = random.randint(64, 700)
        spawn_y   = random.randint(64, 500)
        is_it     = len(players) == 0

        players[sid] = dict(x=spawn_x, y=spawn_y, it=is_it, name=username)

        emit('init',   {'id': sid, 'seed': MAP_SEED, 'players': players})
        emit('playerJoined',
             {'id': sid, 'x': spawn_x, 'y': spawn_y,
              'it': is_it, 'name': username},
             broadcast=True, include_self=False)

    @socketio.on('move')
    def _move(data):
        sid = request.sid
        if sid in players:
            players[sid]['x'] = data['x']
            players[sid]['y'] = data['y']
            emit('playerMoved', {'id': sid, **data}, broadcast=True)

    @socketio.on('tag')
    def _tag(data):
        tagger = request.sid
        target = data.get('id')
        if tagger in players and target in players and players[tagger]['it']:
            players[tagger]['it'] = False
            players[target]['it'] = True
            emit('tagUpdate',
                 {'newIt': target, 'prevIt': tagger},
                 broadcast=True)

    @socketio.on('disconnect')
    def _dc():
        sid    = request.sid
        was_it = players.get(sid, {}).get('it', False)
        if sid in players:
            del players[sid]
        emit('playerLeft', {'id': sid}, broadcast=True)

        if was_it and players:
            new_it = random.choice(list(players.keys()))
            players[new_it]['it'] = True
            emit('tagUpdate',
                 {'newIt': new_it, 'prevIt': sid},
                 broadcast=True)
