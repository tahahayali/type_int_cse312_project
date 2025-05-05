/*  public/js/socket.js  */
export function loadAvatarTexture(scene, key, url) {
  return new Promise(async resolve => {
    if (!url)          return resolve(null);
    if (scene.textures.exists(key)) return resolve(key);  // cached

    /* fetch the image as a blob, turn into Data‑URL */
    const resp = await fetch(url);
    if (!resp.ok)      return resolve(null);

    const blob   = await resp.blob();
    const b64url = await new Promise(res => {
      const fr = new FileReader();
      fr.onload = () => res(fr.result);       // “data:image/png;base64,…”
      fr.readAsDataURL(blob);
    });

    /* when Phaser finishes decoding it fires 'addtexture' */
    const onAdd = textureKey => {
      if (textureKey === key) {
        scene.textures.off('addtexture', onAdd);
        resolve(key);
      }
    };
    scene.textures.on('addtexture', onAdd);

    /* kick off async decode */
    scene.textures.addBase64(key, b64url);
  });
}


/* ─── Network wrapper ──────────────────────────────────────── */
export default class Network {
  constructor(scene) {
    this.scene     = scene;
    this.players   = {};   // id → {container|circle, it, …}
    this.myID      = null;
    this.isIt      = false;
    this.itTimes   = {};
    this.leaderboardVisible = false;

    this.socket = io({ transports: ['websocket'], upgrade: false });

    /* server → client */
    this.socket.on('init',            async data => await this.handleInit(data));
    this.socket.on('playerJoined',    async data => await this.spawn(data));
    this.socket.on('playerMoved',           data => this.move(data));
    this.socket.on('playerLeft',            data => this.remove(data));
    this.socket.on('tagUpdate',             data => this.updateTags(data));
    this.socket.on('leaderboardUpdate',     data => this.updateLeaderboard(data));
  }

  /* ── first snapshot ─────────────────────────────────────── */
  async handleInit(data) {
    this.myID    = data.id;
    this.isIt    = data.players[this.myID].it;
    this.itTimes = data.it_times || {};

    /* spawn ALL players (self + existing) */
    for (const [id, info] of Object.entries(data.players)) {
      await this.spawn({ id, ...info });
    }

    /* create leaderboard UI once */
    if (!this.scene.leaderboard) this.createLeaderboardUI();
    this.updateActivePlayers();
  }

  /* ── spawn (first time or on join) ───────────────────────── */
  async spawn({ id, x, y, it, name = '', avatar }) {
    if (this.players[id]) return;    // already spawned

    /* 1) base circle */
    const circle = this.scene.add
      .circle(0, 0, 16, it ? 0xff0000 : 0x0000ff)
      .setStrokeStyle(it ? 4 : 0, 0xff0000);

    /* 2) optional avatar image */
    let parts = [circle];
    if (avatar) {
      const key = `avt-${id}`;
      const tex = await loadAvatarTexture(this.scene, key, avatar);
      if (tex) {
        const img = this.scene.add.image(0, 0, tex)
                         .setDisplaySize(24, 24)
                         .setOrigin(0.5);
        parts.push(img);
      }
    }

    /* 3) name label (needed for leaderboard) */
    const label = this.scene.add.text(
      0, -24, name || id.slice(0, 4),
      { fontSize: '12px', color: '#fff' }
    ).setOrigin(0.5);
    parts.push(label);

    /* 4) container */
    const container = this.scene.add.container(x, y, parts);

    /* save ref */
    this.players[id] = { id, it, circle, container, label };

    /* self special‑case: enable camera follow */
    if (id === this.myID) {
      this.scene.player          = circle;
      this.scene.playerContainer = container;
      this.scene.cameras.main.startFollow(container);
    }
  }

  /* ── movement from server ───────────────────────────────── */
  move({ id, x, y }) {
  if (id === this.myID) return;
  if (!this.players[id]) return;

   this.players[id].container.setPosition(x, y);
  }

  /* ── player left ────────────────────────────────────────── */
  remove({ id }) {
    const p = this.players[id];
    if (!p) return;
    p.container.destroy(true);
    delete this.players[id];
    this.updateActivePlayers();
  }

  /* ── tag updates ───────────────────────────────────────── */
  updateTags({ newIt, prevIt }) {
    const setItState = (id, isIt) => {
      const p = this.players[id];
      if (!p) return;
      p.it = isIt;
      p.circle.setFillStyle(isIt ? 0xff0000 : 0x0000ff)
              .setStrokeStyle(isIt ? 4 : 0, 0xff0000);
    };
    if (newIt)  setItState(newIt,  true);
    if (prevIt) setItState(prevIt, false);
    if (this.myID === newIt)  this.isIt = true;
    if (this.myID === prevIt) this.isIt = false;
    if (this.scene.updateStatusText) this.scene.updateStatusText();
  }

  /* ── leaderboard push ──────────────────────────────────── */
  updateLeaderboard(data) {
    this.itTimes = data.it_times || {};
    this.updateLeaderboardUI();
  }

  /* ── client → server ───────────────────────────────────── */
  sendMove(x, y) { this.socket.emit('move', { x, y }); }
  sendTag(id)    { this.socket.emit('tag',  { id });   }
  requestLeaderboard() { this.socket.emit('getLeaderboard'); }

  /* ── helper: active players to DOM ─────────────────────── */
  updateActivePlayers() {
    const active = Object.fromEntries(Object.keys(this.players).map(id => [id, true]));
    if (window.updateActivePlayers) window.updateActivePlayers(active);
  }

    /* ---------- leaderboard UI ---------- */
    createLeaderboardUI() {
        const { width, height } = this.scene.game.config;

        // Create toggle button
        const toggleButton = this.scene.add.text(width - 200, 20, "Show Leaderboard", {
            fontSize: '18px',
            backgroundColor: '#333',
            padding: { x: 10, y: 5 },
            color: '#fff'
        })
        .setScrollFactor(0)
        .setDepth(1000)
        .setInteractive({ useHandCursor: true });

        toggleButton.on('pointerdown', () => {
            this.leaderboardVisible = !this.leaderboardVisible;
            toggleButton.setText(this.leaderboardVisible ? "Hide Leaderboard" : "Show Leaderboard");
            this.updateLeaderboardUI();
        });

        // Create leaderboard container
        const leaderboardBg = this.scene.add.rectangle(
            width - 175,
            height / 2,
            300,
            400,
            0x000000,
            0.7
        )
        .setScrollFactor(0)
        .setDepth(999)
        .setVisible(false);

        const leaderboardTitle = this.scene.add.text(
            width - 175,
            height / 2 - 180,
            "LEADERBOARD",
            {
                fontSize: '24px',
                fontStyle: 'bold',
                color: '#ffffff'
            }
        )
        .setOrigin(0.5)
        .setScrollFactor(0)
        .setDepth(1000)
        .setVisible(false);

        const leaderboardSubtitle = this.scene.add.text(
            width - 175,
            height / 2 - 150,
            "Time spent as 'IT'",
            {
                fontSize: '16px',
                color: '#ffffff'
            }
        )
        .setOrigin(0.5)
        .setScrollFactor(0)
        .setDepth(1000)
        .setVisible(false);

        // Create slots for player entries
        const entries = [];
        for (let i = 0; i < 10; i++) {
            const y = height / 2 - 110 + (i * 40);
            const rank = this.scene.add.text(
                width - 305,
                y,
                `${i+1}.`,
                { fontSize: '16px', color: '#ffffff' }
            )
            .setScrollFactor(0)
            .setDepth(1000)
            .setVisible(false);

            const name = this.scene.add.text(
                width - 275,
                y,
                "-",
                { fontSize: '16px', color: '#ffffff' }
            )
            .setScrollFactor(0)
            .setDepth(1000)
            .setVisible(false);

            const time = this.scene.add.text(
                width - 75,
                y,
                "-",
                { fontSize: '16px', color: '#ffffff', align: 'right' }
            )
            .setScrollFactor(0)
            .setDepth(1000)
            .setVisible(false);

            entries.push({ rank, name, time });
        }

        this.scene.leaderboard = {
            toggleButton,
            background: leaderboardBg,
            title: leaderboardTitle,
            subtitle: leaderboardSubtitle,
            entries
        };
    }

    updateLeaderboardUI() {
        this.updateActivePlayers();
        if (!this.scene.leaderboard) return;

        const { toggleButton, background, title, subtitle, entries } = this.scene.leaderboard;

        // Show/hide the leaderboard
        background.setVisible(this.leaderboardVisible);
        title.setVisible(this.leaderboardVisible);
        subtitle.setVisible(this.leaderboardVisible);

        if (!this.leaderboardVisible) {
            entries.forEach(entry => {
                entry.rank.setVisible(false);
                entry.name.setVisible(false);
                entry.time.setVisible(false);
            });

            // Also update DOM leaderboard visibility
            const domLeaderboard = document.getElementById('leaderboard');
            const domToggle = document.getElementById('leaderboard-toggle');
            if (domLeaderboard && domToggle) {
                domLeaderboard.classList.remove('visible');
                domToggle.textContent = 'Show Leaderboard';
            }
            return;
        } else {
            // Update DOM leaderboard visibility
            const domLeaderboard = document.getElementById('leaderboard');
            const domToggle = document.getElementById('leaderboard-toggle');
            if (domLeaderboard && domToggle) {
                domLeaderboard.classList.add('visible');
                domToggle.textContent = 'Hide Leaderboard';
            }
        }

        // Format and sort player times
        const sortedPlayers = [];
        const leaderboardData = {};

        // Only include active players with non-zero times
        for (const id in this.itTimes) {
            // Skip players who aren't active (not in players object)
            if (id !== this.myID && !this.players[id]) {
                continue;
            }

            const time = this.itTimes[id];
            let totalTime = time.total || 0;

            // Add current time if this player is currently "it"
            if (time.started_at) {
                totalTime += (Date.now() / 1000) - time.started_at;
            }

            // Find player name
            let name = id.slice(0, 4); // Default to ID
            if (id === this.myID) {
                name = localStorage.getItem('tag_username') || 'You';
            } else if (this.players[id] && this.players[id].label) {
                name = this.players[id].label.text;
            }

            sortedPlayers.push({
                id,
                name,
                time: totalTime,
                isCurrentPlayer: id === this.myID
            });

            // Add to data for DOM leaderboard
            leaderboardData[id] = {
                ...time,
                name,
                isCurrentPlayer: id === this.myID
            };
        }

        // Sort by time (longest first)
        sortedPlayers.sort((a, b) => b.time - a.time);

        // Update Phaser leaderboard entries
        entries.forEach((entry, i) => {
            if (i < sortedPlayers.length) {
                const player = sortedPlayers[i];

                // Format time as minutes:seconds
                const minutes = Math.floor(player.time / 60);
                const seconds = Math.floor(player.time % 60);
                const timeText = `${minutes}:${seconds.toString().padStart(2, '0')}`;

                entry.rank.setText(`${i+1}.`).setVisible(true);
                entry.name.setText(player.name).setVisible(true);
                entry.time.setText(timeText).setVisible(true);

                // Highlight current player
                if (player.isCurrentPlayer) {
                    entry.name.setColor('#ffff00');
                    entry.time.setColor('#ffff00');
                } else {
                    entry.name.setColor('#ffffff');
                    entry.time.setColor('#ffffff');
                }
            } else {
                entry.rank.setVisible(false);
                entry.name.setVisible(false);
                entry.time.setVisible(false);
            }
        });

        // Update DOM leaderboard if available
        if (window.updateDOMLeaderboard) {
            window.updateDOMLeaderboard(leaderboardData);
        }
    }

}