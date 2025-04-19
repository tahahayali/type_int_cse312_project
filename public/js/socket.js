// Export a class that handles all WebSocket communication
export default class Network {
    constructor(scene) {
        this.scene = scene; // Reference to the Phaser scene
        this.socket = io(); // Auto-connects to the same origin + port
        this.players = {};  // Track all other connected players

        this.myID = null;   // Socket ID of this client
        this.isIt = false;  // Whether this client is currently "it"

        // === Handle 'init' when the server sends full game state ===
        this.socket.on('init', (data) => {
            this.myID = data.id;
            const selfData = data.players[this.myID];
            this.isIt = selfData.it;

            // Set this player's color: red if "it", green if not
            this.scene.player.setFillStyle(this.isIt ? 0xff0000 : 0x00ff00);

            // Create all other players on the map
            for (let id in data.players) {
                if (id === this.myID) continue; // Skip ourself
                const p = data.players[id];
                this.spawnPlayer(id, p.x, p.y, p.it);
            }
        });

        // === A new player joined the game ===
        this.socket.on('playerJoined', (data) => {
            this.spawnPlayer(data.id, data.x, data.y, data.it);
        });

        // === A player moved ===
        this.socket.on('playerMoved', (data) => {
            if (data.id === this.myID) return; // Ignore our own move updates
            const player = this.players[data.id];
            if (player) {
                player.x = data.x;
                player.y = data.y;
            }
        });

        // === A player left the game ===
        this.socket.on('playerLeft', (data) => {
            const p = this.players[data.id];
            if (p) {
                p.destroy();            // Remove their sprite
                delete this.players[data.id]; // Delete from list
            }
        });

        // === Tagging update: someone got tagged ===
        this.socket.on('tagUpdate', (data) => {
            // If we're now "it", update local state and color
            if (data.newIt === this.myID) {
                this.isIt = true;
                this.scene.player.setFillStyle(0xff0000);
            }
            // If we were "it" and lost it
            else if (data.prevIt === this.myID) {
                this.isIt = false;
                this.scene.player.setFillStyle(0x00ff00);
            }

            // Update the visual color of affected remote players
            if (this.players[data.newIt])
                this.players[data.newIt].setFillStyle(0xff0000); // red = "it"

            if (this.players[data.prevIt])
                this.players[data.prevIt].setFillStyle(0x0000ff); // blue = not "it"
        });
    }

    // === Create and display a new player sprite ===
    spawnPlayer(id, x, y, isIt) {
        const color = isIt ? 0xff0000 : 0x0000ff; // Red if "it", blue otherwise
        this.players[id] = this.scene.add.rectangle(x, y, 32, 32, color);
    }

    // === Send our position to the server ===
    sendMove(x, y) {
        this.socket.emit('move', { x, y });
    }

    // === Send a tag event to the server ===
    sendTag(id) {
        if (this.isIt) {
            this.socket.emit('tag', { id });
        }
    }
}
