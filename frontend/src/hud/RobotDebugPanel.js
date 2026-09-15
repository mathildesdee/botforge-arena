// Bottom-left panel shown when a player clicks a robot in the arena.
// For their own robot (if this browser uploaded one — see
// robotDebugger.js) it shows the full rule cascade lighting up as it
// runs (PDF section 27, "logic visualization"): every rule in
// priority order, which ones were checked and found false, which one
// actually won this tick, and which later ones never got reached.
// For any other robot it only shows what a spectator can legitimately
// already see on screen (name, health, energy, position) — never
// another player's decisions, since their program was never sent to
// this browser in the first place.

const HEADER_LINE_HEIGHT = 14;
const RULE_LINE_HEIGHT = 13;
const PANEL_WIDTH = 320;
const PUBLIC_PANEL_HEIGHT = 150;
const PANEL_BOTTOM = 600 - 16;
const MAX_DESCRIPTION_CHARS = 40;

const STATUS_STYLE = {
  matched: { color: '#ffd54f', icon: '▶' },
  else: { color: '#ffd54f', icon: '▶' },
  false: { color: '#7a8699', icon: '·' },
  unreached: { color: '#3d4756', icon: '·' },
};

function truncate(text) {
  return text.length > MAX_DESCRIPTION_CHARS ? `${text.slice(0, MAX_DESCRIPTION_CHARS - 1)}…` : text;
}

export default class RobotDebugPanel {
  constructor(scene) {
    this.scene = scene;

    this.background = scene.add
      .rectangle(16, PANEL_BOTTOM, PANEL_WIDTH, PUBLIC_PANEL_HEIGHT, 0x05070a, 0.85)
      .setOrigin(0, 1)
      .setStrokeStyle(1, 0x2a3442)
      .setDepth(15)
      .setVisible(false);

    this.headerText = scene.add
      .text(26, 0, '', { fontSize: '12px', color: '#e8edf2', lineSpacing: 4 })
      .setDepth(16)
      .setVisible(false);

    this.footerText = scene.add
      .text(26, 0, '', { fontSize: '12px', color: '#e8edf2', fontStyle: 'bold' })
      .setDepth(16)
      .setVisible(false);

    this.ruleLines = []; // pooled Text objects, one per rule — grown as needed, never shrunk
  }

  hide() {
    this.background.setVisible(false);
    this.headerText.setVisible(false);
    this.footerText.setVisible(false);
    this.hideRuleLines();
  }

  showPublicInfo(robot) {
    this.hideRuleLines();
    this.footerText.setVisible(false);
    this.background.setSize(PANEL_WIDTH, PUBLIC_PANEL_HEIGHT).setVisible(true);

    const healthPct = Math.round((robot.health / robot.max_health) * 100);
    this.headerText.setPosition(26, PANEL_BOTTOM - PUBLIC_PANEL_HEIGHT + 10).setVisible(true);
    this.headerText.setText(
      [
        `${robot.name}`,
        `Health: ${healthPct}%`,
        `Energy: ${Math.round(robot.energy)}`,
        `Position: (${Math.round(robot.x)}, ${Math.round(robot.y)})`,
        '',
        "This isn't your robot — its program",
        "isn't sent to your browser.",
      ].join('\n')
    );
  }

  showOwnInfo(robot, debugInfo) {
    const trace = debugInfo.trace || [];
    const healthPct = Math.round((robot.health / robot.max_health) * 100);
    const headerLines = [
      `${robot.name} (you)`,
      `Health: ${healthPct}%   Energy: ${Math.round(robot.energy)}`,
      debugInfo.enemyName ? `Target: ${debugInfo.enemyName} (${debugInfo.enemyDistance})` : 'Target: none visible',
    ];

    const totalHeight =
      20 + headerLines.length * HEADER_LINE_HEIGHT + 6 + trace.length * RULE_LINE_HEIGHT + 6 + HEADER_LINE_HEIGHT;
    const top = PANEL_BOTTOM - totalHeight;

    this.background.setSize(PANEL_WIDTH, totalHeight).setVisible(true);

    let cursorY = top + 10;
    this.headerText.setPosition(26, cursorY).setVisible(true);
    this.headerText.setText(headerLines.join('\n'));
    cursorY += headerLines.length * HEADER_LINE_HEIGHT + 6;

    this.renderRuleLines(trace, cursorY);
    cursorY += trace.length * RULE_LINE_HEIGHT + 6;

    this.footerText.setPosition(26, cursorY).setVisible(true);
    this.footerText.setText(`Action: ${debugInfo.actions.length ? debugInfo.actions.join(' + ') : 'none'}`);
  }

  renderRuleLines(trace, startY) {
    trace.forEach((entry, i) => {
      const style = STATUS_STYLE[entry.status] || STATUS_STYLE.false;
      let line = this.ruleLines[i];
      if (!line) {
        line = this.scene.add.text(26, 0, '', { fontSize: '11px' }).setDepth(16);
        this.ruleLines[i] = line;
      }
      line.setPosition(26, startY + i * RULE_LINE_HEIGHT);
      line.setColor(style.color);
      line.setText(`${style.icon} #${entry.priority} ${truncate(entry.description)}`);
      line.setVisible(true);
    });
    for (let i = trace.length; i < this.ruleLines.length; i++) this.ruleLines[i].setVisible(false);
  }

  hideRuleLines() {
    this.ruleLines.forEach((line) => line.setVisible(false));
  }
}
