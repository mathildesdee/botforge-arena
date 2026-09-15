// Small mute/unmute button, bottom-right corner — deliberately away
// from every other overlay (status top-left, MatchHud top-right,
// RobotDebugPanel bottom-left). Also the one deliberate place that
// calls unlockAudio(): browsers refuse to start an AudioContext
// outside a user gesture, so a click here both toggles the
// preference and (on the first click) actually lets sound play.
import { isMuted, setMuted, unlockAudio } from '../sound.js';

export default class SoundToggle {
  constructor(scene) {
    this.text = scene.add
      .text(784, 588, '', { fontSize: '16px', color: '#e8edf2' })
      .setOrigin(1, 1)
      .setDepth(20)
      .setInteractive({ useHandCursor: true });

    this.render();
    this.text.on('pointerdown', () => {
      unlockAudio();
      setMuted(!isMuted());
      this.render();
    });
  }

  render() {
    this.text.setText(isMuted() ? '🔇' : '🔊');
  }
}
