/*****************************************************
 *  Phaser Multiplayer Tag – main game scene
 *  (guarantees everyone spawns on a free tile)
 *****************************************************/
import Network from './socket.js';

class GameScene extends Phaser.Scene {
  constructor() {
    super('GameScene');
    this.blockedTiles          = new Set();
    this.lastLeaderboardUpdate = 0;
  }

  preload() {
    this.load.image('tiles', '/assets/tilemaps/tiles/buch-dungeon-tileset.png');
  }

  create() {
    /* ── empty map shell (tiles come after we get the shared seed) ── */
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
    this.groundLayer = this.map.createBlankLayer('Ground',  tiles).setScale(this.scaleFactor);
    this.objectLayer = this.map.createBlankLayer('Objects', tiles).setScale(this.scaleFactor);

    /* placeholder player – becomes real after first snapshot */
    this.player = this.add.circle(0, 0, 16, 0x00ff00).setVisible(false);

    this.cursors        = this.input.keyboard.createCursorKeys();
    this.leaderboardKey = this.input.keyboard.addKey(Phaser.Input.Keyboard.KeyCodes.L);

    /* Web-socket wrapper */
    this.network = new Network(this);
    this.network.socket.on('init', data => this.handleInit(data));

    /* ── static UI text ── */
    this.add.text(20, 20, 'Use arrow keys to move', {
      fontSize: '18px', color: '#fff', backgroundColor: '#333', padding: { x: 10, y: 5 }
    }).setScrollFactor(0).setDepth(1000);

    this.add.text(20, 60, 'Press L (or button) to toggle leaderboard', {
      fontSize: '18px', color: '#fff', backgroundColor: '#333', padding: { x: 10, y: 5 }
    }).setScrollFactor(0).setDepth(1000);

    this.statusText = this.add.text(20, 100, '', {
      fontSize: '18px', color: '#fff', backgroundColor: '#333', padding: { x: 10, y: 5 }
    }).setScrollFactor(0).setDepth(1000);

    /* wire any DOM “leaderboard-toggle” button (optional) */
    const domToggle = document.getElementById('leaderboard-toggle');
    if (domToggle) domToggle.addEventListener('click', () => this.toggleLeaderboard());
  }

  /* ───────────────────────── First snapshot from server ───────────────────────── */
  handleInit(data) {
    /* 1. lock RNG so each client builds the SAME dungeon */
    Phaser.Math.RND = new Phaser.Math.RandomDataGenerator([data.seed]);

    /* 2. now we can randomise tiles and mark blocked positions */
    this.randomizeRoom();
    this.recordBlockedTiles();

    /* 3. spawn ourselves – but never on a blocked tile */
    const me       = data.players[data.id];
    const tileSize = this.tileSize * this.scaleFactor;

    let spawnX = me.x;
    let spawnY = me.y;
    const tileX = Math.floor(spawnX / tileSize);
    const tileY = Math.floor(spawnY / tileSize);

    if (this.blockedTiles.has(`${tileX},${tileY}`)) {
      const safe   = this.getSafeSpawn();
      spawnX       = safe.x;
      spawnY       = safe.y;
      this.network.sendMove(spawnX, spawnY);       // tell server right away
    }

    this.player
      .setPosition(spawnX, spawnY)
      .setFillStyle(me.it ? 0xff0000 : 0x00ff00)
      .setStrokeStyle(me.it ? 4 : 0, 0xff0000)
      .setVisible(true);

    this.cameras.main.startFollow(this.player);
    this.cameras.main.setBounds(
      0, 0,
      this.map.width  * this.tileSize * this.scaleFactor,
      this.map.height * this.tileSize * this.scaleFactor
    );

    this.updateStatusText();
  }

  /* ───────────────────────── Every frame ───────────────────────── */
  update() {
    if (!this.player.visible) return;   // still waiting for init()

    const speed = 2.2, ts = this.tileSize * this.scaleFactor;
    let dx = 0, dy = 0;

    if (this.cursors.left.isDown)  dx = -speed;
    else if (this.cursors.right.isDown) dx =  speed;
    if (this.cursors.up.isDown)    dy = -speed;
    else if (this.cursors.down.isDown)  dy =  speed;

    const newX = this.player.x + dx, newY = this.player.y + dy,
          tileXc = Math.floor(this.player.x / ts), tileYc = Math.floor(this.player.y / ts),
          tileXn = Math.floor(newX / ts),          tileYn = Math.floor(newY   / ts),
          blockedX = this.blockedTiles.has(`${tileXn},${tileYc}`),
          blockedY = this.blockedTiles.has(`${tileXc},${tileYn}`);

    let moved = false;
    if (!blockedX) { this.player.x = newX; moved = true; }
    if (!blockedY) { this.player.y = newY; moved = true; }
    if (moved) this.network.sendMove(this.player.x, this.player.y);

    /* collision-based tagging */
    if (this.network.isIt) {
      for (const id in this.network.players) {
        const other = this.network.players[id];
        if (!other) continue;
        const dist = Phaser.Math.Distance.Between(
          this.player.x, this.player.y, other.container.x, other.container.y
        );
        if (dist < 32) {
          this.network.sendTag(id);
          const { circle } = other;
          const s0 = circle.scaleX;
          circle.setScale(1.5);
          this.tweens.add({ targets: circle, scaleX: s0, scaleY: s0, duration: 200, ease: 'Quad.easeOut' });
        }
      }
    }

    /* L key toggles leaderboard */
    if (Phaser.Input.Keyboard.JustDown(this.leaderboardKey)) this.toggleLeaderboard();

    /* refresh leaderboard every second while visible */
    if (this.network?.leaderboardVisible &&
        (!this.lastLeaderboardUpdate || Date.now() - this.lastLeaderboardUpdate > 1000)) {
      this.network.requestLeaderboard();
      this.lastLeaderboardUpdate = Date.now();
    }
  }

  /* ───────────────────────── UI helpers ───────────────────────── */
  toggleLeaderboard() {
    if (!this.network || !this.leaderboard) return;
    this.network.leaderboardVisible = !this.network.leaderboardVisible;
    this.network.updateLeaderboardUI();
    this.leaderboard.toggleButton.setText(this.network.leaderboardVisible ? 'Hide Leaderboard' : 'Show Leaderboard');

    /* keep any DOM leaderboard in sync (optional) */
    const domLb = document.getElementById('leaderboard'),
          domTg = document.getElementById('leaderboard-toggle');
    if (domLb && domTg) {
      if (this.network.leaderboardVisible) {
        domLb.classList.add('visible');  domTg.textContent = 'Hide Leaderboard';
      } else {
        domLb.classList.remove('visible'); domTg.textContent = 'Show Leaderboard';
      }
    }
  }

  updateStatusText() {
    if (this.network.isIt) {
      this.statusText.setText('You are IT! Tag someone!').setColor('#ff0000');
    } else {
      this.statusText.setText('Run! Don’t get tagged!').setColor('#00ff00');
    }
  }

  /* ───────────────────────── Map helpers ───────────────────────── */
  getSafeSpawn() {
    const tileSize = this.tileSize * this.scaleFactor;
    let x, y, tx, ty;
    do {
      x = Phaser.Math.Between(2, this.map.width  - 3) * tileSize;
      y = Phaser.Math.Between(2, this.map.height - 3) * tileSize;
      tx = Math.floor(x / tileSize); ty = Math.floor(y / tileSize);
    } while (this.blockedTiles.has(`${tx},${ty}`));
    return { x, y };
  }

  randomizeRoom() {
    const w = this.map.width, h = this.map.height;
    /* border tiles */
    this.groundLayer.fill(39, 0, 0, w, 1);
    this.groundLayer.fill(1, 0, h - 1, w, 1);
    this.groundLayer.fill(21, 0, 0, 1, h);
    this.groundLayer.fill(19, w - 1, 0, 1, h);
    this.groundLayer.putTileAt(3, 0, 0);
    this.groundLayer.putTileAt(4, w - 1, 0);
    this.groundLayer.putTileAt(22, 0, h - 1);
    this.groundLayer.putTileAt(23, w - 1, h - 1);

    this.groundLayer.weightedRandomize(
      [{ index: 6, weight: 4 }, { index: 7, weight: 1 },
       { index: 8, weight: 1 }, { index: 26, weight: 1 }],
      1, 1, w - 2, h - 2
    );

    this.objectLayer.weightedRandomize(
      [{ index: -1,  weight: 50 }, { index: 13,  weight: 3 },
       { index: 32,  weight: 2 },  { index: 127, weight: 1 },
       { index: 108, weight: 1 },  { index: 109, weight: 2 },
       { index: 110, weight: 2 },  { index: 166, weight: 0.25 },
       { index: 167, weight: 0.25 }],
      1, 1, w - 2, h - 2
    );
  }

  recordBlockedTiles() {
    this.blockedTiles.clear();
    const w = this.map.width, h = this.map.height;

    /* impassable object tiles */
    for (let y = 0; y < h; y++) {
      for (let x = 0; x < w; x++) {
        const t = this.objectLayer.getTileAt(x, y);
        if (t && [13, 32, 127, 108, 109, 110, 166, 167].includes(t.index))
          this.blockedTiles.add(`${x},${y}`);
      }
    }

    /* outer border always blocked */
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

/* ───────────────────────── Launch Phaser ───────────────────────── */
new Phaser.Game({
  type           : Phaser.AUTO,
  width          : window.innerWidth,
  height         : window.innerHeight,
  backgroundColor: '#111',
  pixelArt       : true,
  scene          : GameScene,
  scale          : { mode: Phaser.Scale.FIT, autoCenter: Phaser.Scale.CENTER_BOTH }
});
