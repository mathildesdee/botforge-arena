// Plays back a recorded round (docs/ARCHITECTURE.md #9) by feeding
// its frames to the same BattleRenderer the live Arena uses — a
// replay is just game_state frames from a file instead of a socket.
// Frame pacing matches the backend's tick rate (see
// backend/app/main.py TICK_RATE) so normal playback looks the same
// speed as watching live.

import BattleRenderer from '../battleRenderer.js';
import SoundToggle from '../hud/SoundToggle.js';

const TICK_INTERVAL_MS = 1000 / 20; // backend/app/main.py TICK_RATE = 20

export default class ReplayScene extends Phaser.Scene {
  constructor() {
    super('ReplayScene');
  }

  init({ frames, onFrameChange }) {
    this.frames = frames;
    this.onFrameChange = onFrameChange || (() => {});
    this.frameIndex = 0;
    this.playing = true;
    this.accumMs = 0;
  }

  create() {
    this.add
      .rectangle(400, 300, 800, 600, 0x10151c)
      .setStrokeStyle(2, 0x2a3442);

    this.renderer = new BattleRenderer(this);
    this.soundToggle = new SoundToggle(this);
    this.applyFrame(0);
  }

  update(time, delta) {
    if (!this.playing || this.frames.length === 0) return;

    this.accumMs += delta;
    if (this.accumMs < TICK_INTERVAL_MS) return;
    this.accumMs = 0;

    if (this.frameIndex >= this.frames.length - 1) {
      this.playing = false;
      return;
    }
    this.applyFrame(this.frameIndex + 1);
  }

  applyFrame(index) {
    this.frameIndex = Phaser.Math.Clamp(index, 0, this.frames.length - 1);
    this.renderer.applyState(this.frames[this.frameIndex]);
    this.onFrameChange(this.frameIndex, this.frames.length);
  }

  // Seeking can jump backward, but the renderer's projectile-trail and
  // muzzle-flash/hit-spark logic is diff-based against the previous
  // frame it saw — jumping straight to an arbitrary frame would either
  // leave stale projectiles on screen or spam effects that already
  // happened. Instead, wipe the renderer and fast-forward through
  // every frame up to the target with no per-frame delay: cheap (a
  // few hundred frames of plain data updates) and guarantees the
  // drawn state and internal id-tracking both end up correct.
  seekToFrameIndex(targetIndex) {
    this.playing = false;
    this.renderer.reset();
    const clamped = Phaser.Math.Clamp(targetIndex, 0, this.frames.length - 1);
    this.renderer.silent = true;
    for (let i = 0; i <= clamped; i++) {
      this.renderer.applyState(this.frames[i]);
    }
    this.renderer.silent = false;
    this.frameIndex = clamped;
    this.onFrameChange(this.frameIndex, this.frames.length);
  }

  seekToTick(tick) {
    const index = this.frames.findIndex((f) => f.tick === tick);
    if (index >= 0) this.seekToFrameIndex(index);
  }

  play() {
    if (this.frameIndex >= this.frames.length - 1) {
      this.seekToFrameIndex(0);
    }
    this.playing = true;
  }

  pause() {
    this.playing = false;
  }
}
