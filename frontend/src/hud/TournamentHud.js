// Tournament progress/standings overlay, driven by the tournament_*
// messages (docs/ARCHITECTURE.md #4). A tournament is just several
// matches run back to back, so each pairing's actual battle already
// renders normally through ArenaScene/MatchHud without any changes —
// this only adds the "which pairing, and how did it all end" framing
// around that.
export default class TournamentHud {
  constructor(scene) {
    this.text = scene.add
      .text(16, 32, '', { fontSize: '12px', color: '#a9b4c2', lineSpacing: 3 })
      .setDepth(10);
  }

  setPairing(pairingNumber, totalPairings, participantNames) {
    const vs = participantNames.length ? `: ${participantNames.join(' vs ')}` : '';
    this.text.setText(`Tournament — pairing ${pairingNumber}/${totalPairings}${vs}`);
  }

  setStandings(ranking, names) {
    const lines = ranking.map(
      (row, i) => `${i + 1}. ${names.get(row.participant_id) || row.participant_id} — ${row.points}pts`
    );
    this.text.setText(['Tournament final standings:', ...lines].join('\n'));
  }

  clear() {
    this.text.setText('');
  }
}
