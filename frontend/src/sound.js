// Procedural sound effects via the Web Audio API — no audio files to
// ship, host or license; every effect below is synthesized on the fly
// (oscillators for tones, a noise buffer through a lowpass filter for
// impacts) and disposes of its own nodes once its envelope finishes.
// Purely feedback, same as effects.js — never read by, or fed back
// into, the authoritative game state.

const MUTED_KEY = 'botforge:sound-muted';

let audioCtx = null;
let muted = loadMuted();

function loadMuted() {
  try {
    return localStorage.getItem(MUTED_KEY) === 'true';
  } catch {
    return false; // localStorage unavailable — default to sound on, just don't persist the choice.
  }
}

export function isMuted() {
  return muted;
}

export function setMuted(value) {
  muted = value;
  try {
    localStorage.setItem(MUTED_KEY, String(value));
  } catch {
    // localStorage unavailable — the mute choice just won't survive a reload.
  }
}

function getContext() {
  if (!audioCtx) {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    audioCtx = new AudioContextClass();
  }
  // Browsers start a new AudioContext "suspended" until a user gesture
  // resumes it — call unlockAudio() from inside a click handler.
  if (audioCtx.state === 'suspended') audioCtx.resume();
  return audioCtx;
}

export function unlockAudio() {
  try {
    getContext();
  } catch {
    // Web Audio unsupported in this browser — every playX() below is a no-op via run()'s own try/catch.
  }
}

function run(fn) {
  if (muted) return;
  try {
    fn(getContext());
  } catch {
    // Sound is a nice-to-have; never let a synthesis error interrupt the match.
  }
}

function envelope(ctx, { attack = 0.005, decay, peak }) {
  const gain = ctx.createGain();
  const now = ctx.currentTime;
  gain.gain.setValueAtTime(0, now);
  gain.gain.linearRampToValueAtTime(peak, now + attack);
  gain.gain.exponentialRampToValueAtTime(0.0001, now + attack + decay);
  return gain;
}

function playTone(ctx, { freqStart, freqEnd = freqStart, type = 'sine', duration = 0.12, peak = 0.2 }) {
  const osc = ctx.createOscillator();
  osc.type = type;
  const now = ctx.currentTime;
  osc.frequency.setValueAtTime(freqStart, now);
  if (freqEnd !== freqStart) osc.frequency.exponentialRampToValueAtTime(Math.max(freqEnd, 1), now + duration);

  const gain = envelope(ctx, { decay: duration, peak });
  osc.connect(gain).connect(ctx.destination);
  osc.start(now);
  osc.stop(now + duration + 0.05);
}

function noiseBuffer(ctx, duration) {
  const buffer = ctx.createBuffer(1, Math.max(1, Math.floor(ctx.sampleRate * duration)), ctx.sampleRate);
  const data = buffer.getChannelData(0);
  for (let i = 0; i < data.length; i++) data[i] = Math.random() * 2 - 1;
  return buffer;
}

function playNoise(ctx, { duration = 0.15, peak = 0.3, filterFreqStart = 4000, filterFreqEnd = 200 }) {
  const source = ctx.createBufferSource();
  source.buffer = noiseBuffer(ctx, duration);

  const filter = ctx.createBiquadFilter();
  filter.type = 'lowpass';
  const now = ctx.currentTime;
  filter.frequency.setValueAtTime(filterFreqStart, now);
  filter.frequency.exponentialRampToValueAtTime(Math.max(filterFreqEnd, 20), now + duration);

  const gain = envelope(ctx, { decay: duration, peak });
  source.connect(filter).connect(gain).connect(ctx.destination);
  source.start(now);
  source.stop(now + duration + 0.05);
}

export function playShoot() {
  run((ctx) => playTone(ctx, { freqStart: 900, freqEnd: 220, type: 'square', duration: 0.09, peak: 0.1 }));
}

export function playHit() {
  run((ctx) => playNoise(ctx, { duration: 0.12, peak: 0.22, filterFreqStart: 3000, filterFreqEnd: 300 }));
}

export function playExplosion() {
  run((ctx) => {
    playNoise(ctx, { duration: 0.5, peak: 0.32, filterFreqStart: 2500, filterFreqEnd: 60 });
    playTone(ctx, { freqStart: 120, freqEnd: 40, duration: 0.4, peak: 0.22 });
  });
}

export function playCountdownTick() {
  run((ctx) => playTone(ctx, { freqStart: 440, duration: 0.1, peak: 0.12 }));
}

export function playFightGo() {
  run((ctx) => playTone(ctx, { freqStart: 660, freqEnd: 880, duration: 0.25, peak: 0.18 }));
}

export function playWin() {
  run((ctx) => {
    [523.25, 659.25, 783.99].forEach((freq, i) => {
      const start = ctx.currentTime + i * 0.12;
      const osc = ctx.createOscillator();
      osc.type = 'triangle';
      osc.frequency.value = freq;
      const gain = ctx.createGain();
      gain.gain.setValueAtTime(0, start);
      gain.gain.linearRampToValueAtTime(0.2, start + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.0001, start + 0.3);
      osc.connect(gain).connect(ctx.destination);
      osc.start(start);
      osc.stop(start + 0.35);
    });
  });
}
