// Practice mode: drives one robot with the arrow keys against the
// server's /ws/practice endpoint (backend/app/main.py) to get a feel for
// a build's speed/turn rate — no combat, no lobby, nothing persisted.
// Drawing reuses BattleRenderer, same as the live ArenaScene.

import JsonSocket from '../net/JsonSocket.js';
import BattleRenderer from '../battleRenderer.js';
import { PRACTICE_WS_URL } from '../config.js';
import { PRACTICE_BUILD_KEY } from '../practiceStorage.js';

const STATUS_LABEL = {
  connecting: 'Connecting…',
  connected: 'Connected — use the arrow keys to drive',
  disconnected: 'Disconnected — retrying…',
  error: 'Connection error',
};

export default class PracticeScene extends Phaser.Scene {
  constructor() {
    super('PracticeScene');
    this.lastSentKeys = null;
    this.connected = false;
  }

  create() {
    this.add
      .rectangle(400, 300, 800, 600, 0x10151c)
      .setStrokeStyle(2, 0x2a3442);

    this.statusText = this.add
      .text(16, 12, STATUS_LABEL.connecting, { fontSize: '12px', color: '#7a8699' })
      .setDepth(10);

    this.add
      .text(16, 576, '↑ / ↓ move forward / backward · ← / → turn', { fontSize: '12px', color: '#7a8699' })
      .setDepth(10);

    this.renderer = new BattleRenderer(this);
    this.cursors = this.input.keyboard.createCursorKeys();

    const build = this.loadChosenBuild();
    this.socket = new JsonSocket(PRACTICE_WS_URL, {
      onMessage: (message) => this.handleMessage(message),
      onStatusChange: (status) => {
        this.statusText.setText(STATUS_LABEL[status] || status);
        this.connected = status === 'connected';
        // Send init as the very first thing on a (re)connect, before any
        // input message — the server only honors a custom build if it
        // arrives first (backend/app/main.py's practice_endpoint).
        if (this.connected && build) this.socket.send({ type: 'init', build });
      },
    });
    this.socket.connect();

    this.events.once('shutdown', () => this.socket.disconnect());
  }

  loadChosenBuild() {
    try {
      const raw = sessionStorage.getItem(PRACTICE_BUILD_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null; // sessionStorage unavailable — practice with the server's default build.
    }
  }

  handleMessage(message) {
    if (message.type === 'game_state') this.renderer.applyState(message);
  }

  update() {
    if (!this.connected) return;

    const keys = {
      up: this.cursors.up.isDown,
      down: this.cursors.down.isDown,
      left: this.cursors.left.isDown,
      right: this.cursors.right.isDown,
    };
    const changed = !this.lastSentKeys || Object.keys(keys).some((k) => keys[k] !== this.lastSentKeys[k]);
    if (changed) {
      this.socket.send({ type: 'input', ...keys });
      this.lastSentKeys = keys;
    }
  }
}
