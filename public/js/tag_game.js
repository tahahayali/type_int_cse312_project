import Network from './socket.js';

class TagGame extends Phaser.Scene {
    constructor() {
        super('TagGame');
    }

    preload() {
        this.load.setBaseURL('https://cdn.phaserfiles.com/v385');
        this.load.image('tiles', 'assets/tilemaps/tiles/buch-dungeon-tileset.png');
    }

    create() {
        const tileSize = 16;

        // Tilemap
        this.map = this.make.tilemap({ tileWidth: tileSize, tileHeight: tileSize, width: 23, height: 17 });
        const tiles = this.map.addTilesetImage('tiles');
        this.groundLayer = this.map.createBlankLayer('Ground', tiles).setScale(2);
        this.objectLayer = this.map.createBlankLayer('Objects', tiles).setScale(2);
        this.randomizeRoom();

        this.network = new Network(this);

        // Spawn player at random location
        const spawnX = Phaser.Math.Between(2, this.map.width - 3) * tileSize * 2;
        const spawnY = Phaser.Math.Between(2, this.map.height - 3) * tileSize * 2;
        this.player = this.add.rectangle(spawnX, spawnY, 32, 32, 0x00ff00); // green = self

        this.cursors = this.input.keyboard.createCursorKeys();
    }

    update() {
        const speed = 2;
        let moved = false;

        if (this.cursors.left.isDown) { this.player.x -= speed; moved = true; }
        if (this.cursors.right.isDown) { this.player.x += speed; moved = true; }
        if (this.cursors.up.isDown) { this.player.y -= speed; moved = true; }
        if (this.cursors.down.isDown) { this.player.y += speed; moved = true; }

        if (moved) {
            this.network.sendMove(this.player.x, this.player.y);
        }

        // Tag logic
        for (let id in this.network.players) {
            const other = this.network.players[id];
            const dist = Phaser.Math.Distance.Between(this.player.x, this.player.y, other.x, other.y);
            if (dist < 32) {
                this.network.sendTag(id);
            }
        }
    }

    randomizeRoom() {
        this.groundLayer.weightedRandomize([
            { index: 6, weight: 4 },
            { index: 7, weight: 1 },
            { index: 8, weight: 1 },
            { index: 26, weight: 1 }
        ], 1, 1, this.map.width - 2, this.map.height - 2);
    }
}

const config = {
    type: Phaser.AUTO,
    width: 800,
    height: 600,
    backgroundColor: '#000000',
    scene: TagGame
};

new Phaser.Game(config);
