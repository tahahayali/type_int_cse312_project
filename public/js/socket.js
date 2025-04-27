/*  public/js/socket.js  */
export default class Network {
    constructor(scene) {
        this.scene   = scene;
        this.players = {};
        this.myID    = null;
        this.isIt    = false;

        /* include username if we have it */
        const storedName = localStorage.getItem('tag_username') || '';

        this.socket = io({
            transports: ['websocket'],
            upgrade   : false,
            query     : { username: storedName }
        });

        /* ----- server → client ----- */
        this.socket.on('init',   data => this.handleInit(data));
        this.socket.on('playerJoined', data => this.spawn(data));
        this.socket.on('playerMoved',  data => this.move(data));
        this.socket.on('playerLeft',   data => this.remove(data));
        this.socket.on('tagUpdate',    data => this.updateTags(data));
    }

    /* ---------- event helpers ---------- */
    handleInit(data) {
        this.myID = data.id;
        const me  = data.players[this.myID];
        this.isIt = me.it;

        this.scene.player
            .setFillStyle(this.isIt ? 0xff0000 : 0x00ff00)
            .setStrokeStyle(this.isIt ? 4 : 0, 0xff0000);

        for (const id in data.players) {
            if (id === this.myID) continue;
            const p = data.players[id];
            this.spawn({ id, ...p });
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
        }
    }

    updateTags({ newIt, prevIt }) {
        /* our own status */
        if (newIt === this.myID) {
            this.isIt = true;
            this.scene.player
                .setFillStyle(0xff0000)
                .setStrokeStyle(4, 0xff0000);
        } else if (prevIt === this.myID) {
            this.isIt = false;
            this.scene.player
                .setFillStyle(0x00ff00)
                .setStrokeStyle(0, 0xff0000);
        }

        /* remote players */
        const makeIt = id => {
            const p = this.players[id];
            if (p) {
                p.circle.setFillStyle(0xff0000);
                p.circle.setStrokeStyle(4, 0xff0000);
            }
        };
        const makeNotIt = id => {
            const p = this.players[id];
            if (p) {
                p.circle.setFillStyle(0x0000ff);
                p.circle.setStrokeStyle(0, 0xff0000);
            }
        };
        makeIt(newIt);
        makeNotIt(prevIt);
    }

    /* ---------- client → server ---------- */
    sendMove(x, y) { this.socket.emit('move', { x, y }); }
    sendTag(id)    { if (this.isIt) this.socket.emit('tag', { id }); }
}
