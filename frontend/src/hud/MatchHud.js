// Round counter + live score overlay, driven by the match lifecycle
// messages in docs/ARCHITECTURE.md #2 (round_start/round_end/
// match_end) — not by game_state. Per-robot health is already shown
// as floating bars in the arena itself (see ArenaScene), so this HUD
// only covers what those floating bars can't: whose winning overall.

export default class MatchHud {
  constructor(scene) {
    this.roundText = scene.add
      .text(784, 12, '', { fontSize: '13px', color: '#e8edf2' })
      .setOrigin(1, 0)
      .setDepth(10);

    this.scoreText = scene.add
      .text(784, 32, '', { fontSize: '12px', color: '#a9b4c2', align: 'right' })
      .setOrigin(1, 0)
      .setDepth(10);

    this.totalRounds = null;
  }

  setRound(round, totalRounds) {
    if (totalRounds != null) {
      this.totalRounds = totalRounds;
    }
    const suffix = this.totalRounds ? ` / ${this.totalRounds}` : '';
    this.roundText.setText(`Round ${round}${suffix}`);
  }

  setTotalRounds(totalRounds) {
    this.totalRounds = totalRounds;
  }

  setScores(scores, robotNames = new Map()) {
    if (!scores) return;
    const lines = Object.entries(scores)
      .sort((a, b) => b[1] - a[1])
      .map(([id, score]) => `${robotNames.get(id) || id}: ${score}`);
    this.scoreText.setText(lines.join('\n'));
  }

  setMatchFinished() {
    this.roundText.setText('Match finished');
  }
}
