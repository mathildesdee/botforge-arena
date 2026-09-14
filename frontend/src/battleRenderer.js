// Shared rendering core for anything that draws a battle from
// game_state frames: robots, projectiles, and combat feedback
// (muzzle flashes, hit sparks, explosions — effects.js). Used by both
// ArenaScene (live, fed by JsonSocket) and ReplayScene (fed by a
// recorded frame array) so the actual drawing logic exists in one
// place. Knows nothing about where frames come from.

import { muzzleFlash, hitSpark, explosion } from './effects.js';

const FACING_LENGTH = 26;
const HEALTH_BAR_WIDTH = 40;
const HEALTH_BAR_HEIGHT = 6;

export default class BattleRenderer {
  constructor(scene, { onRobotUpdate } = {}) {
    this.scene = scene;
    this.robotViews = new Map();
    this.robotNames = new Map();
    this.projectileViews = new Map();
    this.onRobotUpdate = onRobotUpdate || (() => {});
  }

  applyState(state) {
    const robots = state.robots || [];
    robots.forEach((robot) => this.upsertRobot(robot, robots));
    this.upsertProjectiles(state.projectiles || []);
    (state.events || []).forEach((event) => this.handleCombatEvent(event));
    return robots;
  }

  handleCombatEvent(event) {
    if (event.type === 'hit') {
      const view = this.robotViews.get(event.target_id);
      if (view) {
        hitSpark(this.scene, view.container.x, view.container.y);
        // Flash red now; the next tick's updateRobotView (a fraction of
        // a second later) naturally restores the correct alive/health
        // color, so there's no need to schedule a manual revert here.
        view.body.setFillStyle(0xff5252);
      }
    } else if (event.type === 'destroyed') {
      const view = this.robotViews.get(event.robot_id);
      if (view) {
        explosion(this.scene, view.container.x, view.container.y);
      }
    }
  }

  upsertRobot(robot, allRobots) {
    this.robotNames.set(robot.id, robot.name);

    let view = this.robotViews.get(robot.id);
    if (!view) {
      view = this.createRobotView(robot.id);
      this.robotViews.set(robot.id, view);
    }
    this.updateRobotView(view, robot);
    this.onRobotUpdate(robot, allRobots);
  }

  createRobotView(robotId) {
    const container = this.scene.add.container(0, 0);
    const body = this.scene.add.circle(0, 0, 18, 0x4fc3f7);
    body.setInteractive({ useHandCursor: true });
    body.on('pointerdown', () => this.scene.onRobotClicked?.(robotId));

    const facing = this.scene.add.graphics();
    const label = this.scene.add
      .text(0, -34, '', { fontSize: '12px', color: '#e8edf2' })
      .setOrigin(0.5, 1);
    const barBg = this.scene.add
      .rectangle(0, -22, HEALTH_BAR_WIDTH, HEALTH_BAR_HEIGHT, 0x2a3442)
      .setOrigin(0.5, 0.5);
    const barFg = this.scene.add
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

  upsertProjectiles(projectiles) {
    const seenIds = new Set();

    projectiles.forEach((p) => {
      seenIds.add(p.id);
      let dot = this.projectileViews.get(p.id);

      if (!dot) {
        // First frame we've seen this projectile — it just fired.
        dot = this.scene.add.circle(p.x, p.y, 4, 0xffca28);
        this.projectileViews.set(p.id, dot);
        const ownerView = this.robotViews.get(p.owner_id);
        if (ownerView) {
          muzzleFlash(this.scene, ownerView.container.x, ownerView.container.y, p.direction);
        }
      } else {
        // Leave a quickly-fading ghost at the old spot before moving —
        // over consecutive frames this reads as a motion trail.
        const ghost = this.scene.add.circle(dot.x, dot.y, 3, 0xffca28, 0.35);
        this.scene.tweens.add({ targets: ghost, alpha: 0, duration: 150, onComplete: () => ghost.destroy() });
      }

      dot.setPosition(p.x, p.y);
    });

    for (const [id, dot] of this.projectileViews) {
      if (!seenIds.has(id)) {
        dot.destroy();
        this.projectileViews.delete(id);
      }
    }
  }

  // Wipes every drawn view and internal id-tracking so the next
  // applyState starts clean — needed when a replay seeks backward,
  // since the diff-based projectile/effect logic above assumes frames
  // are always applied forward in order.
  reset() {
    for (const view of this.robotViews.values()) view.container.destroy();
    for (const dot of this.projectileViews.values()) dot.destroy();
    this.robotViews.clear();
    this.projectileViews.clear();
  }
}
