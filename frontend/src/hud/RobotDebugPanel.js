// Bottom-left panel shown when a player clicks a robot in the arena.
// For their own robot (if this browser uploaded one — see
// robotDebugger.js) it shows live target/rule/action reasoning; for
// any other robot it only shows what a spectator can legitimately
// already see on screen (name, health, energy, position) — never
// another player's decisions, since their program was never sent to
// this browser in the first place.

export default class RobotDebugPanel {
  constructor(scene) {
    this.background = scene.add
      .rectangle(16, 600 - 16, 260, 150, 0x05070a, 0.85)
      .setOrigin(0, 1)
      .setStrokeStyle(1, 0x2a3442)
      .setDepth(15)
      .setVisible(false);

    this.text = scene.add
      .text(26, 600 - 26, '', { fontSize: '12px', color: '#e8edf2', lineSpacing: 4 })
      .setOrigin(0, 1)
      .setDepth(16)
      .setVisible(false);
  }

  hide() {
    this.background.setVisible(false);
    this.text.setVisible(false);
  }

  showPublicInfo(robot) {
    this.background.setVisible(true);
    this.text.setVisible(true);
    const healthPct = Math.round((robot.health / robot.max_health) * 100);
    this.text.setText(
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
    this.background.setVisible(true);
    this.text.setVisible(true);
    const healthPct = Math.round((robot.health / robot.max_health) * 100);
    this.text.setText(
      [
        `${robot.name} (you)`,
        `Health: ${healthPct}%   Energy: ${Math.round(robot.energy)}`,
        `Target: ${debugInfo.enemyName || 'none visible'}`,
        debugInfo.enemyDistance != null ? `Enemy distance: ${debugInfo.enemyDistance}` : '',
        `Rule #${debugInfo.rulePriority ?? '—'}: ${debugInfo.ruleDescription}`,
        `Action: ${debugInfo.actions.length ? debugInfo.actions.join(' + ') : 'none'}`,
      ]
        .filter(Boolean)
        .join('\n')
    );
  }
}
