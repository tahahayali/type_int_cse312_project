/*  public/js/socket.js  */
export default class Network {
    constructor(scene) {
        this.scene     = scene;
        this.players   = {};
        this.myID      = null;
        this.isIt      = false;
        this.itTimes   = {};  // Store "it" times for leaderboard
        this.leaderboardVisible = false; // Track if leaderboard is visible

        /* include username if we have it */
        const storedName = localStorage.getItem('tag_username') || '';

        this.socket = io({
            transports: ['websocket'],
            upgrade   : false,
            query     : { username: storedName }
        });

        /* ----- server → client ----- */
        this.socket.on('init',           data => this.handleInit(data));
        this.socket.on('playerJoined',   data => this.spawn(data));
        this.socket.on('playerMoved',    data => this.move(data));
        this.socket.on('playerLeft',     data => this.remove(data));
        this.socket.on('tagUpdate',      data => this.updateTags(data));
        this.socket.on('leaderboardUpdate', data => this.updateLeaderboard(data));

        // Add debugging for socket events
        this.socket.onAny((event, ...args) => {
            console.log(`Socket event: ${event}`, args);
        });
    }

    /* ---------- event helpers ---------- */
    handleInit(data) {
        this.myID = data.id;
        const me  = data.players[this.myID];
        this.isIt = me.it;
        this.itTimes = data.it_times || {};

        console.log(`Initial state - myID: ${this.myID}, isIt: ${this.isIt}`);

        this.scene.player
            .setFillStyle(this.isIt ? 0xff0000 : 0x00ff00)
            .setStrokeStyle(this.isIt ? 4 : 0, 0xff0000);

        for (const id in data.players) {
            if (id === this.myID) continue;
            const p = data.players[id];
            this.spawn({ id, ...p });
        }

        // Create leaderboard UI if not already created
        if (!this.scene.leaderboard) {
            this.createLeaderboardUI();
        }
    }

    spawn({ id, x, y, it, name = '' }) {
        const circle = this.scene.add
            .circle(0, 0, 16, it ? 0xff0000 : 0x0000ff)
            .setStrokeStyle(it ? 4 : 0, 0xff0000);

        const label  = this.scene.add
            .text(0, -24, name || id.slice(0, 4), { fontSize: '12px', color: '#fff' })
            .setOrigin(0.5);

        const container = this.scene.add.container(x, y, [circle, label]);
        this.players[id] = { container, circle, label };

        console.log(`Spawned player ${id} at (${x}, ${y}), it: ${it}`);
    }

    move({ id, x, y }) {
        if (id === this.myID) return;
        const entry = this.players[id];
        if (entry) {
            entry.container.x = x;
            entry.container.y = y;
        }
    }

    remove({ id }) {
        const entry = this.players[id];
        if (entry) {
            entry.container.destroy(true);
            delete this.players[id];
            console.log(`Player ${id} removed`);
        }
    }

    updateTags({ newIt, prevIt }) {
        console.log(`Tag update - newIt: ${newIt}, prevIt: ${prevIt}, myID: ${this.myID}`);

        /* our own status */
        if (newIt === this.myID) {
            this.isIt = true;
            this.scene.player
                .setFillStyle(0xff0000)
                .setStrokeStyle(4, 0xff0000);
            console.log('I am now IT!');
        } else if (prevIt === this.myID) {
            this.isIt = false;
            this.scene.player
                .setFillStyle(0x00ff00)
                .setStrokeStyle(0, 0xff0000);
            console.log('I am no longer IT!');
        }

        /* remote players */
        const makeIt = id => {
            const p = this.players[id];
            if (p) {
                p.circle.setFillStyle(0xff0000);
                p.circle.setStrokeStyle(4, 0xff0000);
                console.log(`Player ${id} is now IT`);
            }
        };
        const makeNotIt = id => {
            const p = this.players[id];
            if (p) {
                p.circle.setFillStyle(0x0000ff);
                p.circle.setStrokeStyle(0, 0xff0000);
                console.log(`Player ${id} is no longer IT`);
            }
        };

        if (newIt) makeIt(newIt);
        if (prevIt) makeNotIt(prevIt);

        // Update status text if available
        if (this.scene.updateStatusText) {
            this.scene.updateStatusText();
        }
    }

    updateLeaderboard(data) {
        this.itTimes = data.it_times || {};
        this.updateLeaderboardUI();
    }

    /* ---------- client → server ---------- */
    sendMove(x, y) {
        this.socket.emit('move', { x, y });
    }

    sendTag(id) {
        if (this.isIt) {
            console.log(`Sending tag event for player ${id}`);
            this.socket.emit('tag', { id });
        } else {
            console.log('Not IT, cannot tag');
        }
    }

    requestLeaderboard() {
        this.socket.emit('getLeaderboard');
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

        for (const id in this.itTimes) {
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