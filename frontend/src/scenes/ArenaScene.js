// Renders a game_state snapshot (see docs/ARCHITECTURE.md #1) as a top-down
// arena. This scene only draws whatever data it's given — it never decides
// positions or outcomes itself. Right now that data is static mock JSON;
// a later issue swaps the source for live WebSocket messages without
// needing to change how robots are drawn.

const ROBOT_RADIUS = 18;
const FACING_LENGTH = 26;
const HEALTH_BAR_WIDTH = 40;
const HEALTH_BAR_HEIGHT = 6;

export default class ArenaScene extends Phaser.Scene {
  constructor() {
    super('ArenaScene');
  }

  preload() {
    this.load.json('gameState', 'src/mock/game_state.mock.json');
  }

  create() {
    const state = this.cache.json.get('gameState');

    this.add
      .rectangle(400, 300, 800, 600, 0x10151c)
      .setStrokeStyle(2, 0x2a3442);

    this.add
      .text(16, 12, 'Static mock render — no live connection yet', {
        fontSize: '12px',
        color: '#7a8699',
      })
      .setDepth(10);

    state.robots.forEach((robot) => this.renderRobot(robot));
    state.projectiles.forEach((projectile) => this.renderProjectile(projectile));
  }

  renderRobot(robot) {
    const container = this.add.container(robot.x, robot.y);

    const body = this.add.circle(0, 0, ROBOT_RADIUS, robot.alive ? 0x4fc3f7 : 0x555f6b);

    const rad = Phaser.Math.DegToRad(robot.direction);
    const facing = this.add.graphics();
    facing.lineStyle(3, 0xffffff, 1);
    facing.lineBetween(0, 0, Math.cos(rad) * FACING_LENGTH, Math.sin(rad) * FACING_LENGTH);

    const label = this.add
      .text(0, -34, robot.name, { fontSize: '12px', color: '#e8edf2' })
      .setOrigin(0.5, 1);

    const healthRatio = Phaser.Math.Clamp(robot.health / robot.max_health, 0, 1);
    const barBg = this.add
      .rectangle(0, -22, HEALTH_BAR_WIDTH, HEALTH_BAR_HEIGHT, 0x2a3442)
      .setOrigin(0.5, 0.5);
    const barFg = this.add
      .rectangle(
        -HEALTH_BAR_WIDTH / 2,
        -22,
        HEALTH_BAR_WIDTH * healthRatio,
        HEALTH_BAR_HEIGHT,
        healthRatio > 0.3 ? 0x4caf50 : 0xe53935
      )
      .setOrigin(0, 0.5);

    container.add([body, facing, label, barBg, barFg]);
  }

  renderProjectile(projectile) {
    this.add.circle(projectile.x, projectile.y, 4, 0xffca28);
  }
}
