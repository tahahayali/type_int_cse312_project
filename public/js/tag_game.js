/*****************************************************
 *  Phaser Multiplayer Tag – main game scene
 *  (guarantees everyone spawns on a free tile)
 *****************************************************/

import Network from './socket.js';

class GameScene extends Phaser.Scene {
  constructor() {
    super('GameScene');
    this.blockedTiles = new Set();
    this.lastLeaderboardUpdate = 0;
    this.dungeonBuilt = false;
    this.activeToasts = []; // Track active toast notifications
    this.shownAchievements = new Set(); // Track which achievements have been shown
  }

  preload() {
    this.load.image('tiles', '/assets/tilemaps/tiles/buch-dungeon-tileset.png');
  }

  create() {
    /* ── empty map shell (tiles come after we get the shared seed) ── */
    this.tileSize = 16;
    this.scaleFactor = 3;
    this.mapWidth = 60;
    this.mapHeight = 40;

    this.map = this.make.tilemap({
      tileWidth: this.tileSize,
      tileHeight: this.tileSize,
      width: this.mapWidth,
      height: this.mapHeight
    });

    const tiles = this.map.addTilesetImage('tiles');
    this.groundLayer = this.map.createBlankLayer('Ground', tiles).setScale(this.scaleFactor);
    this.objectLayer = this.map.createBlankLayer('Objects', tiles).setScale(this.scaleFactor);

    /* placeholder player – becomes real after first snapshot */
    this.player = this.add.circle(0, 0, 16, 0x00ff00).setVisible(false);

    this.cursors = this.input.keyboard.createCursorKeys();
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

  /* Achievement toast notification system */
  showAchievementToast(data) {
    console.log('Showing achievement toast:', data);

    // Check if we've already shown this achievement in this session
    const achievementKey = data.achievement;
    if (this.shownAchievements.has(achievementKey)) {
      console.log(`Achievement ${achievementKey} already shown, skipping toast`);
      return;
    }

    // Mark this achievement as shown
    this.shownAchievements.add(achievementKey);

    // Get achievement icon based on type
    let iconClass = 'fa-trophy';
    let iconColor = '#f1c40f';

    if (data.achievement === 'first_tag') {
      iconClass = 'fa-tag';
    } else if (data.achievement === 'survivor_10min') {
      iconClass = 'fa-stopwatch';
    } else if (data.achievement === 'survivor_1hour') {
      iconClass = 'fa-medal';
    }

    // Create toast DOM element
    const toast = document.createElement('div');
    toast.className = 'achievement-toast';
    toast.innerHTML = `
      <div class="toast-icon"><i class="fas ${iconClass}" style="color: ${iconColor};"></i></div>
      <div class="toast-content">
        <div class="toast-title">Achievement Unlocked!</div>
        <div class="toast-message">${data.name}: ${data.description}</div>
      </div>
    `;

    document.body.appendChild(toast);

    // Try to play a sound effect if available
    try {
      const audio = new Audio('/assets/sounds/achievement.mp3');
      audio.volume = 0.5;
      audio.play().catch(err => console.log('Audio play failed:', err));
    } catch (err) {
      console.log('No achievement sound available');
    }

    // Add to active toasts array
    if (!this.activeToasts) this.activeToasts = [];
    this.activeToasts.push(toast);

    // Position and show with animation
    setTimeout(() => {
      toast.classList.add('show');
      this.updateToastPositions();
    }, 100);

    // Remove after display
    setTimeout(() => {
      toast.classList.remove('show');
      setTimeout(() => {
        toast.remove();
        const index = this.activeToasts.indexOf(toast);
        if (index > -1) {
          this.activeToasts.splice(index, 1);
        }
        this.updateToastPositions();
      }, 500);
    }, 5000);
  }

  // Update positions of multiple toasts
  updateToastPositions() {
    if (!this.activeToasts || this.activeToasts.length <= 1) return;

    let currentOffset = 0;
    for (let i = 0; i < this.activeToasts.length; i++) {
      const toast = this.activeToasts[i];
      if (!toast) continue;

      toast.style.bottom = `${30 + currentOffset}px`;
      currentOffset += toast.offsetHeight + 10; // 10px gap between toasts
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
})()