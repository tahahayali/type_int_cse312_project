// Import the Network class that handles all WebSocket communication
import Network from './socket.js';

class TagGame extends Phaser.Scene {
    constructor() {
        super('TagGame'); // Register the scene with Phaser
    }

    preload() {
        // Set the base URL for assets
        this.load.setBaseURL('https://cdn.phaserfiles.com/v385');

        // Load the tile image that will be used in the dungeon tilemap
        this.load.image('tiles', 'assets/tilemaps/tiles/buch-dungeon-tileset.png');
    }

    create() {
        const tileSize = 16; // Base tile size (in pixels)

        // === Setup the Tilemap ===
        this.map = this.make.tilemap({
            tileWidth: tileSize,
            tileHeight: tileSize,
            width: 23,
            height: 17
        });

        const tiles = this.map.addTilesetImage('tiles');

        // Create layers for ground and objects (scaled for visibility)
        this.groundLayer = this.map.createBlankLayer('Ground', tiles).setScale(2);
        this.objectLayer = this.map.createBlankLayer('Objects', tiles).setScale(2);

        // Randomize the room with decorative tiles
        this.randomizeRoom();

        // === Setup WebSocket communication ===
        this.network = new Network(this); // Pass this Phaser scene to Network

        // === Spawn local player at random location within bounds ===
        const spawnX = Phaser.Math.Between(2, this.map.width - 3) * tileSize * 2;
        const spawnY = Phaser.Math.Between(2, this.map.height - 3) * tileSize * 2;

        // Represent the local player with a rectangle (green by default)
        this.player = this.add.rectangle(spawnX, spawnY, 32, 32, 0x00ff00);

        // Setup arrow key input
        this.cursors = this.input.keyboard.createCursorKeys();
    }

    update() {
        const speed = 2;
        let moved = false;

        // === Handle movement input ===
        if (this.cursors.left.isDown) {
            this.player.x -= speed;
            moved = true;
        }
        if (this.cursors.right.isDown) {
            this.player.x += speed;
            moved = true;
        }
        if (this.cursors.up.isDown) {
            this.player.y -= speed;
            moved = true;
        }
        if (this.cursors.down.isDown) {
            this.player.y += speed;
            moved = true;
        }

        // If player moved, emit new position to the server
        if (moved) {
            this.network.sendMove(this.player.x, this.player.y);
        }

        // === Tagging Logic ===
        // Loop through all other players
        for (let id in this.network.players) {
            const other = this.network.players[id];

            // Check distance between local player and each remote player
            const dist = Phaser.Math.Distance.Between(
                this.player.x, this.player.y,
                other.x, other.y
            );

            // If close enough, attempt to tag
            if (dist < 32) {
                this.network.sendTag(id);
            }
        }
    }

    // === Randomize the floor with weighted tiles ===
    randomizeRoom() {
        this.groundLayer.weightedRandomize([
            { index: 6, weight: 4 },   // Main floor tile
            { index: 7, weight: 1 },   // Variation
            { index: 8, weight: 1 },   // Variation
            { index: 26, weight: 1 }   // Variation
        ],
        1, 1,                         // Top-left corner (tile coordinates)
        this.map.width - 2,          // Width of randomization area
        this.map.height - 2          // Height of randomization area
        );
    }
}

// === Phaser Game Configuration ===
const config = {
    type: Phaser.AUTO,             // Auto-select WebGL or Canvas renderer
    width: 800,
    height: 600,
    backgroundColor: '#000000',
    scene: TagGame                 // Register the TagGame scene
};

// === Launch the Game ===
new Phaser.Game(config);
