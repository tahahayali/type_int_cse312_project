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
    this.dungeonBuilt          = false;
    this.toasts                = []; // Array to track active toast notifications
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

    this.network.socket.on('init', data => this.buildDungeon(data.seed));

    /* ── static UI text ── */
    this.add.text(20, 20, 'Use arrow keys to move', {
      fontSize: '18px', color: '#fff', backgroundColor: '#333', padding: { x: 10, y: 5 }
    }).setScrollFactor(0).setDepth(1000);

    this.add.text(20, 0, 'Reverse Tag: Stay IT longest!', {
      fontSize: '14px',
      color: '#aaa',
      backgroundColor: '#222',
      padding: { x: 8, y: 3 }
    }).setScrollFactor(0).setDepth(1000);


    this.add.text(20, 60, 'Press L (or button) to toggle leaderboard', {
      fontSize: '18px', color: '#fff', backgroundColor: '#333', padding: { x: 10, y: 5 }
    }).setScrollFactor(0).setDepth(1000);

    this.statusText = this.add.text(20, 100, '', {
      fontSize: '18px', color: '#fff', backgroundColor: '#333', padding: { x: 10, y: 5 }
    }).setScrollFactor(0).setDepth(1000);

    /* wire any DOM "leaderboard-toggle" button (optional) */
    const domToggle = document.getElementById('leaderboard-toggle');
    if (domToggle) domToggle.addEventListener('click', () => this.toggleLeaderboard());
  }
     buildDungeon(seed) {
    if (this.dungeonBuilt) return;
    Phaser.Math.RND = new Phaser.Math.RandomDataGenerator([seed]);
    this.randomizeRoom();
    this.recordBlockedTiles();
    this.dungeonBuilt = true;
  }


 /* ───────────────────────── Every frame ───────────────────────── */
  update() {
    const mover = this.playerContainer || this.player;
    if (!mover.visible && !this.playerContainer) return;   // not spawned yet

    /* movement input */
    const speed = 2.2, ts = this.tileSize * this.scaleFactor;
    let dx = 0, dy = 0;
    if (this.cursors.left.isDown)  dx = -speed;
    else if (this.cursors.right.isDown) dx =  speed;
    if (this.cursors.up.isDown)    dy = -speed;
    else if (this.cursors.down.isDown)  dy =  speed;

    /* wall collision */
    const newX = mover.x + dx, newY = mover.y + dy,
          tileXc = Math.floor(mover.x / ts), tileYc = Math.floor(mover.y / ts),
          tileXn = Math.floor(newX  / ts),   tileYn = Math.floor(newY  / ts),
          blockedX = this.blockedTiles.has(`${tileXn},${tileYc}`),
          blockedY = this.blockedTiles.has(`${tileXc},${tileYn}`);

    let moved = false;
    if (!blockedX) { mover.x = newX; moved = true; }
    if (!blockedY) { mover.y = newY; moved = true; }
    if (moved) this.network.sendMove(mover.x, mover.y);

    /* bump‑to‑tag (reverse tag) */
    if (!this.network.isIt) {
      for (const p of Object.values(this.network.players)) {
        if (!p.it) continue;
        const dist = Phaser.Math.Distance.Between(
          mover.x, mover.y, p.container.x, p.container.y);
        if (dist < 32) {
          this.network.sendTag(p.id);
          break;
        }
      }
    }

    /* leaderboard maintenance */
    if (Phaser.Input.Keyboard.JustDown(this.leaderboardKey)) this.toggleLeaderboard();
    if (this.network.leaderboardVisible &&
        (!this.lastLeaderboardUpdate || Date.now() - this.lastLeaderboardUpdate > 1000)) {
      this.network.requestLeaderboard();
      this.lastLeaderboardUpdate = Date.now();
    }
    /* Update toast positions if needed */
    this.updateToastPositions();
  }

  /* ───────────────────────── Achievement Toast ───────────────────────── */
  showAchievementToast(data) {
    // Check if this achievement has already been shown (using localStorage)
    const shownAchievements = JSON.parse(localStorage.getItem('shownAchievements') || '{}');

    // If this achievement is already shown, don't show it again
    if (shownAchievements[data.achievement]) {
      return;
    }

    // Mark this achievement as shown
    shownAchievements[data.achievement] = true;
    localStorage.setItem('shownAchievements', JSON.stringify(shownAchievements));

    const { width, height } = this.game.config;

    // Create toast container
    const toastY = height - 100 - (this.toasts.length * 80);
    const toast = this.add.container(width - 200, toastY).setScrollFactor(0).setDepth(2000);

    // Add toast background
    const bg = this.add.rectangle(0, 0, 350, 70, 0x000000, 0.8).setOrigin(0.5);
    toast.add(bg);

    // Add achievement icon
    const icon = this.add.text(-150, 0, '🏆', { fontSize: '32px' }).setOrigin(0.5);
    toast.add(icon);

    // Add achievement text
    const title = this.add.text(-80, -15, data.name, {
      fontSize: '18px',
      fontStyle: 'bold',
      color: '#ffffff'
    }).setOrigin(0, 0.5);

    const desc = this.add.text(-80, 15, data.description, {
      fontSize: '14px',
      color: '#cccccc'
    }).setOrigin(0, 0.5);

    toast.add(title);
    toast.add(desc);

    // Track this toast
    this.toasts.push(toast);

    // Animate in
    this.tweens.add({
      targets: toast,
      x: width - 200,
      duration: 500,
      ease: 'Back.easeOut',
      onComplete: () => {
        // After 5 seconds, animate out and destroy
        this.time.delayedCall(5000, () => {
          this.tweens.add({
            targets: toast,
            x: width + 400,
            duration: 500,
            ease: 'Back.easeIn',
            onComplete: () => {
              // Remove from array and destroy
              this.toasts = this.toasts.filter(t => t !== toast);
              toast.destroy();
              this.updateToastPositions();
            }
          });
        });
      }
    });
  }

  // Keep toasts positioned correctly when they're removed
  updateToastPositions() {
    const { height } = this.game.config;
    this.toasts.forEach((toast, index) => {
      this.tweens.add({
        targets: toast,
        y: height - 100 - (index * 80),
        duration: 200,
        ease: 'Power2'
      });
    });
  }

   /* ───────────────────────── UI helpers ───────────────────────── */
  toggleLeaderboard() {
    if (!this.network || !this.leaderboard) return;
    this.network.leaderboardVisible = !this.network.leaderboardVisible;
    this.network.updateLeaderboardUI();
    this.leaderboard.toggleButton.setText(
      this.network.leaderboardVisible ? 'Hide Leaderboard' : 'Show Leaderboard'
    );

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
      this.statusText.setText('Stay IT! Run from others!').setColor('#ff0000');
    } else {
      this.statusText.setText('Chase the IT player!').setColor('#00ff00');
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
(async () => {
  const res = await fetch('/api/current-user');
  if (!res.ok) return (window.location.href = '/');
  new Phaser.Game({
    type: Phaser.AUTO,
    width: window.innerWidth,
    height: window.innerHeight,
    backgroundColor: '#111',
    pixelArt: true,
    scene: GameScene,
    scale: { mode: Phaser.Scale.FIT, autoCenter: Phaser.Scale.CENTER_BOTH }
  });
})();