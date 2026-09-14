// Live arena: connects to /ws and renders whatever it's told (see
// docs/ARCHITECTURE.md #1-#2, #4). Drawing itself (robots, projectiles,
// combat effects) lives in battleRenderer.js, shared with ReplayScene
// — this file only owns the live-connection and match/tournament/
// debug-panel concerns on top of that shared core.

import JsonSocket from '../net/JsonSocket.js';
import MatchHud from '../hud/MatchHud.js';
import TournamentHud from '../hud/TournamentHud.js';
import RobotDebugPanel from '../hud/RobotDebugPanel.js';
import BattleRenderer from '../battleRenderer.js';
import { showBanner, showCountdown } from '../effects.js';
import { createRobotDebugger } from '../robotDebugger.js';
import { MY_PLAYER_ID_KEY, MY_ROBOT_KEY } from '../robotDebuggerStorage.js';
import { WS_URL } from '../config.js';

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
    this.selectedRobotId = null;
    this.myPlayerId = null;
    this.myRobotDebugger = null;
    this.lastDebugTickAt = null;
    this.tournamentNames = new Map();
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
    this.renderer = new BattleRenderer(this, {
      onRobotUpdate: (robot, allRobots) => {
        if (this.selectedRobotId === robot.id) this.refreshDebugPanel(robot, allRobots);
      },
    });
    this.onRobotClicked = (robotId) => this.handleRobotClicked(robotId);
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
        this.renderer.applyState(message);
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
        this.hud.setScores(message.scores, this.renderer.robotNames);
        break;
      case 'match_end': {
        this.hud.setScores(message.final_scores, this.renderer.robotNames);
        this.hud.setMatchFinished();
        const winnerName = this.renderer.robotNames.get(message.winner_id) || 'Nobody';
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

  handleRobotClicked(robotId) {
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
}
