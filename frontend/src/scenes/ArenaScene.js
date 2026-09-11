// Renders whatever game_state messages it's given (see
// docs/ARCHITECTURE.md #1). This scene never decides positions or
// outcomes itself — it just reflects state coming over the wire from
// GameSocket. Robot/projectile views are created once per id and then
// updated in place so movement reads as continuous rather than a
// full redraw every tick.

import GameSocket from '../net/GameSocket.js';
import { WS_URL } from '../config.js';

const FACING_LENGTH = 26;
const HEALTH_BAR_WIDTH = 40;
const HEALTH_BAR_HEIGHT = 6;

const STATUS_LABEL = {
  connecting: 'Connecting…',
  connected: 'Connected',
  disconnected: 'Disconnected — retrying…',
  error: 'Connection error',
};

export default class ArenaScene extends Phaser.Scene {
  constructor() {
    super('ArenaScene');
    this.robotViews = new Map();
    this.projectileViews = [];
  }

  create() {
    this.add
      .rectangle(400, 300, 800, 600, 0x10151c)
      .setStrokeStyle(2, 0x2a3442);

    this.statusText = this.add
      .text(16, 12, STATUS_LABEL.connecting, { fontSize: '12px', color: '#7a8699' })
      .setDepth(10);

    this.gameSocket = new GameSocket(WS_URL, {
      onGameState: (state) => this.applyState(state),
      onStatusChange: (status) => this.statusText.setText(STATUS_LABEL[status] || status),
    });
    this.gameSocket.connect();

    this.events.once('shutdown', () => this.gameSocket.disconnect());
  }

  applyState(state) {
    (state.robots || []).forEach((robot) => this.upsertRobot(robot));
    this.redrawProjectiles(state.projectiles || []);
  }

  upsertRobot(robot) {
    let view = this.robotViews.get(robot.id);
    if (!view) {
      view = this.createRobotView();
      this.robotViews.set(robot.id, view);
    }
    this.updateRobotView(view, robot);
  }

  createRobotView() {
    const container = this.add.container(0, 0);
    const body = this.add.circle(0, 0, 18, 0x4fc3f7);
    const facing = this.add.graphics();
    const label = this.add
      .text(0, -34, '', { fontSize: '12px', color: '#e8edf2' })
      .setOrigin(0.5, 1);
    const barBg = this.add
      .rectangle(0, -22, HEALTH_BAR_WIDTH, HEALTH_BAR_HEIGHT, 0x2a3442)
      .setOrigin(0.5, 0.5);
    const barFg = this.add
      .rectangle(-HEALTH_BAR_WIDTH / 2, -22, HEALTH_BAR_WIDTH, HEALTH_BAR_HEIGHT, 0x4caf50)
      .setOrigin(0, 0.5);

    container.add([body, facing, label, barBg, barFg]);

    return { container, body, facing, label, barFg };
  }

  updateRobotView(view, robot) {
    view.container.setPosition(robot.x, robot.y);
    view.body.setFillStyle(robot.alive ? 0x4fc3f7 : 0x555f6b);
    view.label.setText(robot.name);

    const rad = Phaser.Math.DegToRad(robot.direction);
    view.facing.clear();
    view.facing.lineStyle(3, 0xffffff, 1);
    view.facing.lineBetween(0, 0, Math.cos(rad) * FACING_LENGTH, Math.sin(rad) * FACING_LENGTH);

    const healthRatio = Phaser.Math.Clamp(robot.health / robot.max_health, 0, 1);
    view.barFg.width = HEALTH_BAR_WIDTH * healthRatio;
    view.barFg.fillColor = healthRatio > 0.3 ? 0x4caf50 : 0xe53935;
  }

  redrawProjectiles(projectiles) {
    this.projectileViews.forEach((view) => view.destroy());
    this.projectileViews = projectiles.map((p) => this.add.circle(p.x, p.y, 4, 0xffca28));
  }
}
