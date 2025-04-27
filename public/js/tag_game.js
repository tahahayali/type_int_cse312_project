import Network from './socket.js';

class GameScene extends Phaser.Scene {
    constructor() {
        super('GameScene');
        this.blockedTiles = new Set();
    }

    preload() {
        this.load.image('tiles', '/assets/tilemaps/tiles/buch-dungeon-tileset.png');
    }

    create() {
        /* empty map shell – tiles come AFTER we get the shared seed */
        this.tileSize    = 16;
        this.scaleFactor = 3;
        this.mapWidth    = 60;
        this.mapHeight   = 40;

        this.map = this.make.tilemap({
            tileWidth : this.tileSize,
            tileHeight: this.tileSize,
            width     : this.mapWidth,
            height    : this.mapHeight
        });

        const tiles      = this.map.addTilesetImage('tiles');
        this.groundLayer = this.map.createBlankLayer('Ground',  tiles)
                                   .setScale(this.scaleFactor);
        this.objectLayer = this.map.createBlankLayer('Objects', tiles)
                                   .setScale(this.scaleFactor);

        /* placeholder player – becomes real after init() */
        this.player = this.add.circle(0, 0, 16, 0x00ff00).setVisible(false);

        this.cursors = this.input.keyboard.createCursorKeys();

        // Add leaderboard toggle key
        this.leaderboardKey = this.input.keyboard.addKey(Phaser.Input.Keyboard.KeyCodes.L);

        /* WebSocket wrapper (hooks into our scene automatically) */
        this.network = new Network(this);

        /* we handle RNG + map once we get the first snapshot */
        this.network.socket.on('init', data => this.handleInit(data));

        // Add game instructions
        const { width, height } = this.game.config;
        this.add.text(20, 20, 'Use arrow keys to move', {
            fontSize: '18px',
            color: '#ffffff',
            backgroundColor: '#333333',
            padding: { x: 10, y: 5 }
        })
        .setScrollFactor(0)
        .setDepth(1000);

        this.add.text(20, 60, 'Press L or click button to toggle leaderboard', {
            fontSize: '18px',
            color: '#ffffff',
            backgroundColor: '#333333',
            padding: { x: 10, y: 5 }
        })
        .setScrollFactor(0)
        .setDepth(1000);

        // Status indicator text
        this.statusText = this.add.text(20, 100, '', {
            fontSize: '18px',
            color: '#ffffff',
            backgroundColor: '#333333',
            padding: { x: 10, y: 5 }
        })
        .setScrollFactor(0)
        .setDepth(1000);

        // Connect DOM toggle button to Phaser if it exists
        const domToggle = document.getElementById('leaderboard-toggle');
        if (domToggle) {
            domToggle.addEventListener('click', () => {
                if (this.network && this.leaderboard) {
                    this.network.leaderboardVisible = !this.network.leaderboardVisible;
                    this.network.updateLeaderboardUI();
                    this.leaderboard.toggleButton.setText(
                        this.network.leaderboardVisible ? "Hide Leaderboard" : "Show Leaderboard"
                    );

                    // Also sync with DOM leaderboard
                    const domLeaderboard = document.getElementById('leaderboard');
                    if (domLeaderboard) {
                        if (this.network.leaderboardVisible) {
                            domLeaderboard.classList.add('visible');
                            domToggle.textContent = 'Hide Leaderboard';
                        } else {
                            domLeaderboard.classList.remove('visible');
                            domToggle.textContent = 'Show Leaderboard';
                        }
                    }
                }
            });
        }
    }

    /* first snapshot from server */
    handleInit(data) {
        /* lock Phaser RNG – everyone builds the SAME dungeon */
        Phaser.Math.RND = new Phaser.Math.RandomDataGenerator([data.seed]);

        this.randomizeRoom();
        this.recordBlockedTiles();

        /* place our circle where the server told us */
        const me = data.players[data.id];
        this.player
            .setPosition(me.x, me.y)
            .setFillStyle(me.it ? 0xff0000 : 0x00ff00)
            .setStrokeStyle(me.it ? 4 : 0, 0xff0000)
            .setVisible(true);

        this.cameras.main.startFollow(this.player);
        this.cameras.main.setBounds(
            0, 0,
            this.map.width  * this.tileSize * this.scaleFactor,
            this.map.height * this.tileSize * this.scaleFactor
        );

        // Set initial status text
        this.updateStatusText();
    }

    updateStatusText() {
        if (this.network.isIt) {
            this.statusText.setText('You are IT! Tag someone else!').setColor('#ff0000');
        } else {
            this.statusText.setText('Run away! Don\'t get tagged!').setColor('#00ff00');
        }
    }

    update() {
        if (!this.player.visible) return;           // still waiting for init

        const speed = 2.2,
              ts    = this.tileSize * this.scaleFactor;

        let dx = 0, dy = 0;
        if (this.cursors.left.isDown)  dx = -speed;
        else if (this.cursors.right.isDown) dx = speed;
        if (this.cursors.up.isDown)    dy = -speed;
        else if (this.cursors.down.isDown)  dy = speed;

        const newX = this.player.x + dx,
              newY = this.player.y + dy;

        const tileXc = Math.floor(this.player.x / ts),
              tileYc = Math.floor(this.player.y / ts),
              tileXn = Math.floor(newX         / ts),
              tileYn = Math.floor(newY         / ts);

        const blockedX = this.blockedTiles.has(`${tileXn},${tileYc}`),
              blockedY = this.blockedTiles.has(`${tileXc},${tileYn}`);

        let moved = false;
        if (!blockedX) { this.player.x = newX; moved = true; }
        if (!blockedY) { this.player.y = newY; moved = true; }

        if (moved) this.network.sendMove(this.player.x, this.player.y);

        /* check for tag collisions */
        if (this.network.isIt) {
            for (const id in this.network.players) {
                const other = this.network.players[id];
                if (!other) continue;
                const { container } = other;

                // Calculate distance between player and target
                const dist = Phaser.Math.Distance.Between(
                    this.player.x, this.player.y, container.x, container.y
                );

                // If close enough to tag
                if (dist < 32) {
                    console.log(`Attempting to tag player ${id}, distance: ${dist}`);
                    this.network.sendTag(id);

                    // Visual feedback for tag attempt
                    this.cameras.main.flash(100, 255, 0, 0);
                }
            }
        }

        // Toggle leaderboard with L key
        if (Phaser.Input.Keyboard.JustDown(this.leaderboardKey)) {
            if (this.network && this.leaderboard) {
                this.network.leaderboardVisible = !this.network.leaderboardVisible;
                this.network.updateLeaderboardUI();
                this.leaderboard.toggleButton.setText(
                    this.network.leaderboardVisible ? "Hide Leaderboard" : "Show Leaderboard"
                );

                // Also sync with DOM leaderboard
                const domLeaderboard = document.getElementById('leaderboard');
                const domToggle = document.getElementById('leaderboard-toggle');
                if (domLeaderboard && domToggle) {
                    if (this.network.leaderboardVisible) {
                        domLeaderboard.classList.add('visible');
                        domToggle.textContent = 'Hide Leaderboard';
                    } else {
                        domLeaderboard.classList.remove('visible');
                        domToggle.textContent = 'Show Leaderboard';
                    }
                }
            }
        }

        // Update leaderboard every 1 second
        if (this.network && this.network.leaderboardVisible) {
            if (!this.lastLeaderboardUpdate || Date.now() - this.lastLeaderboardUpdate > 1000) {
                this.network.requestLeaderboard();
                this.lastLeaderboardUpdate = Date.now();
            }
        }
    }

    /* ─── map building (unchanged from before) ─── */
    randomizeRoom() {
        const w = this.map.width, h = this.map.height;
        this.groundLayer.fill(39, 0, 0, w, 1);
        this.groundLayer.fill(1, 0, h - 1, w, 1);
        this.groundLayer.fill(21, 0, 0, 1, h);
        this.groundLayer.fill(19, w - 1, 0, 1, h);
        this.groundLayer.putTileAt(3, 0, 0);
        this.groundLayer.putTileAt(4, w - 1, 0);
        this.groundLayer.putTileAt(23, w - 1, h - 1);
        this.groundLayer.putTileAt(22, 0, h - 1);

        this.groundLayer.weightedRandomize(
            [{ index: 6, weight: 4 }, { index: 7, weight: 1 },
             { index: 8, weight: 1 }, { index: 26, weight: 1 }],
            1, 1, w - 2, h - 2
        );

        this.objectLayer.weightedRandomize(
            [{ index: -1, weight: 50 }, { index: 13, weight: 3 },
             { index: 32, weight: 2 },  { index: 127, weight: 1 },
             { index: 108, weight: 1 }, { index: 109, weight: 2 },
             { index: 110, weight: 2 }, { index: 166, weight: 0.25 },
             { index: 167, weight: 0.25 }],
            1, 1, w - 2, h - 2
        );
    }

    recordBlockedTiles() {
        this.blockedTiles.clear();
        const w = this.map.width, h = this.map.height;
        for (let y = 0; y < h; y++) {
            for (let x = 0; x < w; x++) {
                const tile = this.objectLayer.getTileAt(x, y);
                if (!tile) continue;
                if ([13, 32, 127, 108, 109, 110, 166, 167].includes(tile.index))
                    this.blockedTiles.add(`${x},${y}`);
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
}

new Phaser.Game({
  type: Phaser.AUTO,
  width: window.innerWidth,
  height: window.innerHeight,
  backgroundColor: '#111',
  pixelArt: true,
  scene: GameScene,
  scale: { mode: Phaser.Scale.FIT, autoCenter: Phaser.Scale.CENTER_BOTH }
});