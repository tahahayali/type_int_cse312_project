// Export a class that handles all WebSocket communication
export default class Network {
    constructor(scene) {
        this.scene = scene;
        this.socket = io();
        this.players = {};
        this.myID = null;
        this.isIt = false;

        this.socket.on('init', (data) => {
            this.myID = data.id;
            const selfData = data.players[this.myID];
            this.isIt = selfData.it;

            this.scene.player.setFillStyle(this.isIt ? 0xff0000 : 0x00ff00);

            for (let id in data.players) {
                if (id === this.myID) continue;
                const p = data.players[id];
                this.spawnPlayer(id, p.x, p.y, p.it);
            }
        });

        this.socket.on('playerJoined', (data) => {
            this.spawnPlayer(data.id, data.x, data.y, data.it);
        });

        this.socket.on('playerMoved', (data) => {
            if (data.id === this.myID) return;
            const player = this.players[data.id];
            if (player) {
                player.x = data.x;
                player.y = data.y;
            }
        });

        this.socket.on('playerLeft', (data) => {
            const p = this.players[data.id];
            if (p) {
                p.destroy();
                delete this.players[data.id];
            }
        });

        this.socket.on('tagUpdate', (data) => {
            if (data.newIt === this.myID) {
                this.isIt = true;
                this.scene.player.setFillStyle(0xff0000);
            } else if (data.prevIt === this.myID) {
                this.isIt = false;
                this.scene.player.setFillStyle(0x00ff00);
            }

            if (this.players[data.newIt])
                this.players[data.newIt].setFillStyle(0xff0000);

            if (this.players[data.prevIt])
                this.players[data.prevIt].setFillStyle(0x0000ff);
        });
    }

    spawnPlayer(id, x, y, isIt) {
        const color = isIt ? 0xff0000 : 0x0000ff;
        this.players[id] = this.scene.add.rectangle(x, y, 32, 32, color);
    }

    sendMove(x, y) {
        this.socket.emit('move', { x, y });
    }

    sendTag(id) {
        if (this.isIt) {
            this.socket.emit('tag', { id });
        }
    }
}
