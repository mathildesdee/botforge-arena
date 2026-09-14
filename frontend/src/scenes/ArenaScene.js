// Renders whatever messages it's given over the WebSocket (see
// docs/ARCHITECTURE.md #1-#2). This scene never decides positions,
// scores, or outcomes itself — it just reflects state coming over the
// wire from JsonSocket. Robot/projectile views are created once per
// id and then updated in place so movement reads as continuous
// rather than a full redraw every tick. Visual feedback (muzzle
// flashes, explosions, banners) lives in effects.js, kept separate
// from this state-reflecting logic.

import JsonSocket from '../net/JsonSocket.js';
import MatchHud from '../hud/MatchHud.js';
import TournamentHud from '../hud/TournamentHud.js';
import RobotDebugPanel from '../hud/RobotDebugPanel.js';
import { muzzleFlash, hitSpark, explosion, showBanner, showCountdown } from '../effects.js';
import { createRobotDebugger } from '../robotDebugger.js';
import { MY_PLAYER_ID_KEY, MY_ROBOT_KEY } from '../robotDebuggerStorage.js';
import { WS_URL } from '../config.js';

const FACING_LENGTH = 26;
const HEALTH_BAR_WIDTH = 40;
const HEALTH_BAR_HEIGHT = 6;
const MAX_DEBUG_DT = 0.2; // clamp so a backgrounded tab doesn't report a huge gap

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
    this.robotNames = new Map();
    this.tournamentNames = new Map();
    this.projectileViews = new Map();
    this.selectedRobotId = null;
    this.myPlayerId = null;
    this.myRobotDebugger = null;
    this.lastDebugTickAt = null;
  }

  create() {
    this.add
      .rectangle(400, 300, 800, 600, 0x10151c)
      .setStrokeStyle(2, 0x2a3442);

    this.statusText = this.add
      .text(16, 12, STATUS_LABEL.connecting, { fontSize: '12px', color: '#7a8699' })
      .setDepth(10);

    this.hud = new MatchHud(this);
    this.tournamentHud = new TournamentHud(this);
    this.debugPanel = new RobotDebugPanel(this);
    this.loadOwnRobot();

    this.gameSocket = new JsonSocket(WS_URL, {
      onMessage: (message) => this.handleMessage(message),
      onStatusChange: (status) => this.statusText.setText(STATUS_LABEL[status] || status),
    });
    this.gameSocket.connect();

    this.events.once('shutdown', () => this.gameSocket.disconnect());
  }

  loadOwnRobot() {
    // Enables full debug info (target/rule/action) for whichever robot
    // this browser uploaded via the Lobby — see robotDebugger.js for
    // why that's the only robot this can ever work for.
    try {
      this.myPlayerId = localStorage.getItem(MY_PLAYER_ID_KEY);
      const robotJson = localStorage.getItem(MY_ROBOT_KEY);
      if (robotJson) {
        this.myRobotDebugger = createRobotDebugger(JSON.parse(robotJson));
      }
    } catch {
      // localStorage unavailable or corrupt — clicking your own robot
      // will just show the same public-only info as anyone else's.
    }
  }

  handleMessage(message) {
    switch (message.type) {
      case 'game_state':
        this.applyState(message);
        break;
      case 'match_start':
        this.hud.setTotalRounds(message.total_rounds);
        showCountdown(this);
        break;
      case 'round_start':
        this.hud.setRound(message.round, message.total_rounds);
        showBanner(this, `Round ${message.round}`, { holdMs: 700 });
        break;
      case 'round_end':
        this.hud.setScores(message.scores, this.robotNames);
        break;
      case 'match_end': {
        this.hud.setScores(message.final_scores, this.robotNames);
        this.hud.setMatchFinished();
        const winnerName = this.robotNames.get(message.winner_id) || 'Nobody';
        showBanner(this, `🏆 ${winnerName} wins!`, { holdMs: 2500, color: '#ffd54f' });
        break;
      }
      case 'tournament_start':
        message.participants.forEach((p) => this.tournamentNames.set(p.id, p.name));
        this.tournamentHud.setPairing(0, message.total_pairings, []);
        showBanner(this, `Tournament starting — ${message.total_pairings} pairings`, { holdMs: 1500 });
        break;
      case 'tournament_pairing_start': {
        const names = message.participants.map((id) => this.tournamentNames.get(id) || id);
        this.tournamentHud.setPairing(message.pairing, message.total_pairings, names);
        break;
      }
      case 'tournament_end':
        this.tournamentHud.setStandings(message.ranking, this.tournamentNames);
        showBanner(this, '🏆 Tournament complete!', { holdMs: 2500, color: '#ffd54f' });
        break;
      default:
        // tournament_pairing_end isn't rendered separately — each
        // pairing already gets the normal match_end winner banner
        // above, so a second summary here would just be redundant.
        break;
    }
  }

  applyState(state) {
    const robots = state.robots || [];
    robots.forEach((robot) => this.upsertRobot(robot, robots));
    this.upsertProjectiles(state.projectiles || []);
    (state.events || []).forEach((event) => this.handleCombatEvent(event));
  }

  handleCombatEvent(event) {
    if (event.type === 'hit') {
      const view = this.robotViews.get(event.target_id);
      if (view) {
        hitSpark(this, view.container.x, view.container.y);
        // Flash red now; the next tick's updateRobotView (a fraction of
        // a second later) naturally restores the correct alive/health
        // color, so there's no need to schedule a manual revert here.
        view.body.setFillStyle(0xff5252);
      }
    } else if (event.type === 'destroyed') {
      const view = this.robotViews.get(event.robot_id);
      if (view) {
        explosion(this, view.container.x, view.container.y);
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

    if (this.selectedRobotId === robot.id) {
      this.refreshDebugPanel(robot, allRobots);
    }
  }

  createRobotView(robotId) {
    const container = this.add.container(0, 0);
    const body = this.add.circle(0, 0, 18, 0x4fc3f7);
    body.setInteractive({ useHandCursor: true });
    body.on('pointerdown', () => this.onRobotClicked(robotId));

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

  onRobotClicked(robotId) {
    if (this.selectedRobotId === robotId) {
      this.selectedRobotId = null;
      this.debugPanel.hide();
      return;
    }
    this.selectedRobotId = robotId;
    this.lastDebugTickAt = null;
  }

  refreshDebugPanel(robot, allRobots) {
    if (robot.id === this.myPlayerId && this.myRobotDebugger) {
      const now = performance.now();
      const dt = this.lastDebugTickAt ? Math.min((now - this.lastDebugTickAt) / 1000, MAX_DEBUG_DT) : 0.05;
      this.lastDebugTickAt = now;

      const others = allRobots.filter((r) => r.id !== robot.id);
      const debugInfo = this.myRobotDebugger.evaluate(robot, others, dt);
      this.debugPanel.showOwnInfo(robot, debugInfo);
    } else {
      this.debugPanel.showPublicInfo(robot);
    }
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
        dot = this.add.circle(p.x, p.y, 4, 0xffca28);
        this.projectileViews.set(p.id, dot);
        const ownerView = this.robotViews.get(p.owner_id);
        if (ownerView) {
          muzzleFlash(this, ownerView.container.x, ownerView.container.y, p.direction);
        }
      } else {
        // Leave a quickly-fading ghost at the old spot before moving —
        // over consecutive frames this reads as a motion trail.
        const ghost = this.add.circle(dot.x, dot.y, 3, 0xffca28, 0.35);
        this.tweens.add({ targets: ghost, alpha: 0, duration: 150, onComplete: () => ghost.destroy() });
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
}
