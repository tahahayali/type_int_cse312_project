export default class Network {
    constructor(scene) {
        this.scene = scene;
        this.socket = io("http://localhost:5000");

        this.players = {};

        this.socket.on("init", (data) => {
            this.id = data.id;
            for (let id in data.players) {
                if (id !== this.id) {
                    const p = data.players[id];
                    this.spawnPlayer(id, p.x, p.y);
                }
            }
        });

        this.socket.on("playerJoined", (data) => {
            this.spawnPlayer(data.id, data.x, data.y);
        });

        this.socket.on("playerMoved", (data) => {
            if (data.id === this.id) return;
            const player = this.players[data.id];
            if (player) {
                player.setPosition(data.x, data.y);
            }
        });

        this.socket.on("playerLeft", (data) => {
            if (this.players[data.id]) {
                this.players[data.id].destroy();
                delete this.players[data.id];
            }
        });

        this.socket.on("tagUpdate", (data) => {
            if (this.players[data.id]) {
                this.players[data.id].setFillStyle(0xff0000); // red = "it"
            }
        });
    }

    spawnPlayer(id, x, y) {
        const rect = this.scene.add.rectangle(x, y, 32, 32, 0x0000ff);
        this.players[id] = rect;
    }

    sendMove(x, y) {
        this.socket.emit("move", { x, y });
    }

    sendTag(id) {
        this.socket.emit("tag", { id });
    }
}
