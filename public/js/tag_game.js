import Network from './socket.js';

class GameScene extends Phaser.Scene {
    constructor() {
        super('GameScene');
    }

    preload() {
        this.load.image('tiles', '/assets/tilemaps/tiles/buch-dungeon-tileset.png');
    }

    create() {
        this.tileSize = 16;
        this.scaleFactor = 3;
        const mapWidth = 60, mapHeight = 40;

        this.map = this.make.tilemap({
            tileWidth: this.tileSize,
            tileHeight: this.tileSize,
            width: mapWidth,
            height: mapHeight
        });

        const tiles = this.map.addTilesetImage('tiles');
        this.groundLayer = this.map.createBlankLayer('Ground', tiles).setScale(this.scaleFactor);
        this.objectLayer = this.map.createBlankLayer('Objects', tiles).setScale(this.scaleFactor);

        this.randomizeRoom();
        this.blockedTiles = new Set();
        this.recordBlockedTiles();

        this.network = new Network(this);

        const spawn = this.getSafeSpawn(mapWidth, mapHeight);
        this.player = this.add.circle(spawn.x, spawn.y, 16, 0x00ff00);

        this.cameras.main.startFollow(this.player);
        this.cameras.main.setBounds(
            0, 0,
            this.map.width * this.tileSize * this.scaleFactor,
            this.map.height * this.tileSize * this.scaleFactor
        );

        this.network.sendMove(this.player.x, this.player.y);

        this.cursors = this.input.keyboard.createCursorKeys();
    }

    update() {
        const speed = 2.2;
        const tileSize = this.tileSize * this.scaleFactor;
        let moveX = 0, moveY = 0;

        if (this.cursors.left.isDown) moveX = -speed;
        else if (this.cursors.right.isDown) moveX = speed;
        if (this.cursors.up.isDown) moveY = -speed;
        else if (this.cursors.down.isDown) moveY = speed;

        const newX = this.player.x + moveX;
        const newY = this.player.y + moveY;

        const tileX_current = Math.floor(this.player.x / tileSize);
        const tileY_current = Math.floor(this.player.y / tileSize);
        const tileX_new = Math.floor(newX / tileSize);
        const tileY_new = Math.floor(newY / tileSize);

        const blockedX = this.blockedTiles.has(`${tileX_new},${tileY_current}`);
        const blockedY = this.blockedTiles.has(`${tileX_current},${tileY_new}`);

        let moved = false;

        if (!blockedX) {
            this.player.x = newX;
            moved = true;
        }

        if (!blockedY) {
            this.player.y = newY;
            moved = true;
        }

        if (moved) {
            this.network.sendMove(this.player.x, this.player.y);
        }

        if (this.network.isIt) {
            for (let id in this.network.players) {
                const other = this.network.players[id];
                if (!other) continue;
                const dist = Phaser.Math.Distance.Between(this.player.x, this.player.y, other.x, other.y);
                if (dist < 32) {
                    this.network.sendTag(id);
                }
            }
        }
    }

    randomizeRoom() {
        const w = this.map.width;
        const h = this.map.height;

        this.groundLayer.fill(39, 0, 0, w, 1);
        this.groundLayer.fill(1, 0, h - 1, w, 1);
        this.groundLayer.fill(21, 0, 0, 1, h);
        this.groundLayer.fill(19, w - 1, 0, 1, h);

        this.groundLayer.putTileAt(3, 0, 0);
        this.groundLayer.putTileAt(4, w - 1, 0);
        this.groundLayer.putTileAt(23, w - 1, h - 1);
        this.groundLayer.putTileAt(22, 0, h - 1);

        this.groundLayer.weightedRandomize([
            { index: 6, weight: 4 },
            { index: 7, weight: 1 },
            { index: 8, weight: 1 },
            { index: 26, weight: 1 }
        ], 1, 1, w - 2, h - 2);

        this.objectLayer.weightedRandomize([
            { index: -1, weight: 50 },
            { index: 13, weight: 3 },
            { index: 32, weight: 2 },
            { index: 127, weight: 1 },
            { index: 108, weight: 1 },
            { index: 109, weight: 2 },
            { index: 110, weight: 2 },
            { index: 166, weight: 0.25 },
            { index: 167, weight: 0.25 }
        ], 1, 1, w - 2, h - 2);
    }

    recordBlockedTiles() {
        this.blockedTiles.clear();
        const w = this.map.width, h = this.map.height;
        for (let y = 0; y < h; y++) {
            for (let x = 0; x < w; x++) {
                const tile = this.objectLayer.getTileAt(x, y);
                if (!tile) continue;
                const blockIndexes = [13, 32, 127, 108, 109, 110, 166, 167];
                if (blockIndexes.includes(tile.index)) {
                    this.blockedTiles.add(`${x},${y}`);
                }
            }
        }
        for (let x = 0; x < w; x++) {
            this.blockedTiles.add(`${x},0`);
            this.blockedTiles.add(`${x},${h - 1}`);
        }
        for (let y = 0; y < h; y++) {
            this.blockedTiles.add(`0,${y}`);
            this.blockedTiles.add(`${w - 1},${y}`);
        }
    }

    getSafeSpawn(mapWidth, mapHeight) {
        let spawnX, spawnY, tileX, tileY;
        const tileSize = this.tileSize * this.scaleFactor;
        do {
            spawnX = Phaser.Math.Between(2, mapWidth - 3) * tileSize;
            spawnY = Phaser.Math.Between(2, mapHeight - 3) * tileSize;
            tileX = Math.floor(spawnX / tileSize);
            tileY = Math.floor(spawnY / tileSize);
        } while (this.blockedTiles.has(`${tileX},${tileY}`));
        return { x: spawnX, y: spawnY };
    }
}

const config = {
    type: Phaser.AUTO,
    width: window.innerWidth,
    height: window.innerHeight,
    backgroundColor: '#111',
    pixelArt: true,
    scene: GameScene,
    scale: {
        mode: Phaser.Scale.FIT,
        autoCenter: Phaser.Scale.CENTER_BOTH
    }
};

new Phaser.Game(config);
