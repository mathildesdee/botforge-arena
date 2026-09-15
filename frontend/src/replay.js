// Browse and play back recorded rounds (docs/ARCHITECTURE.md #9).
// Fetches the index, then a full recording on demand, and drives
// ReplayScene the same way index.html drives ArenaScene — just with
// playback controls instead of a live connection.

import ReplayScene from './scenes/ReplayScene.js';
import { REPLAYS_URL } from './config.js';
import { unlockAudio } from './sound.js';

const listViewEl = document.getElementById('replay-list-view');
const listEl = document.getElementById('replay-list');
const viewerViewEl = document.getElementById('replay-viewer-view');
const backButton = document.getElementById('back-to-list-button');
const playPauseButton = document.getElementById('play-pause-button');
const scrubberEl = document.getElementById('replay-scrubber');
const positionEl = document.getElementById('replay-position');
const markersEl = document.getElementById('replay-markers');

let game = null;
let scrubberIsBeingDragged = false;

function formatDuration(seconds) {
  return `${Math.round(seconds)}s`;
}

function renderList(replays) {
  listEl.innerHTML = '';
  if (replays.length === 0) {
    listEl.innerHTML = '<p class="empty-note">No replays yet — play a match in the Lobby first.</p>';
    return;
  }

  replays.forEach((entry) => {
    const item = document.createElement('div');
    item.className = 'replay-item';

    const info = document.createElement('div');
    info.innerHTML = `<strong>Round ${entry.round_number}</strong> (match #${entry.match_id})<br><span class="replay-meta">Winner: ${
      entry.winner_name || 'draw'
    } — ${formatDuration(entry.duration_seconds)}</span>`;

    const watchButton = document.createElement('button');
    watchButton.type = 'button';
    watchButton.className = 'primary';
    watchButton.textContent = 'Watch';
    watchButton.addEventListener('click', () => {
      unlockAudio(); // real user gesture — the one place autoplay-blocked audio can start
      loadReplay(entry.round_result_id);
    });

    item.append(info, watchButton);
    listEl.appendChild(item);
  });
}

async function loadReplay(roundResultId) {
  const response = await fetch(`${REPLAYS_URL}/${roundResultId}`);
  const data = await response.json();
  if (!data.found) {
    alert('This replay could not be found.');
    return;
  }
  openViewer(data);
}

function openViewer(recording) {
  listViewEl.hidden = true;
  viewerViewEl.hidden = false;

  scrubberEl.min = 0;
  scrubberEl.max = recording.frames.length - 1;
  scrubberEl.value = 0;
  playPauseButton.textContent = 'Pause';

  if (game) {
    game.destroy(true);
  }

  // Don't list ReplayScene in config.scene — Phaser would auto-boot it
  // with no init data before this function's own scene.add() call
  // could run, calling create() against an undefined frames array.
  // scene.add(key, class, autoStart, data) starts it exactly once,
  // already carrying the data init() needs.
  const config = {
    type: Phaser.AUTO,
    width: 800,
    height: 600,
    parent: 'replay-arena',
    backgroundColor: '#0b0e13',
  };
  game = new Phaser.Game(config);
  game.scene.add('ReplayScene', ReplayScene, true, {
    frames: recording.frames,
    onFrameChange: (index, total) => {
      if (!scrubberIsBeingDragged) scrubberEl.value = index;
      positionEl.textContent = `Tick ${recording.frames[index].tick} — frame ${index + 1}/${total}`;
      if (index >= total - 1) playPauseButton.textContent = 'Replay';
    },
  });

  renderMarkers(recording);
}

function renderMarkers(recording) {
  markersEl.innerHTML = '';
  const scene = () => game.scene.getScene('ReplayScene');

  const addButton = (label, tick) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = label;
    button.disabled = tick == null;
    button.addEventListener('click', () => scene().seekToTick(tick));
    markersEl.appendChild(button);
  };

  addButton('First shot', recording.markers.first_shot);
  addButton('First hit', recording.markers.first_hit);
  addButton('Final kill', recording.markers.final_kill);

  const namesById = new Map((recording.frames[0]?.robots || []).map((r) => [r.id, r.name]));
  Object.entries(recording.health_markers || {}).forEach(([robotId, thresholds]) => {
    const name = namesById.get(robotId) || robotId;
    addButton(`${name} below 50%`, thresholds.below_50);
    addButton(`${name} below 20%`, thresholds.below_20);
  });
}

playPauseButton.addEventListener('click', () => {
  const scene = game.scene.getScene('ReplayScene');
  if (playPauseButton.textContent === 'Pause') {
    scene.pause();
    playPauseButton.textContent = 'Play';
  } else {
    scene.play();
    playPauseButton.textContent = 'Pause';
  }
});

scrubberEl.addEventListener('input', () => {
  scrubberIsBeingDragged = true;
  game.scene.getScene('ReplayScene').seekToFrameIndex(Number(scrubberEl.value));
  playPauseButton.textContent = 'Play';
});
scrubberEl.addEventListener('change', () => {
  scrubberIsBeingDragged = false;
});

backButton.addEventListener('click', () => {
  if (game) {
    game.destroy(true);
    game = null;
  }
  viewerViewEl.hidden = true;
  listViewEl.hidden = false;
});

fetch(REPLAYS_URL)
  .then((response) => response.json())
  .then(renderList)
  .catch((err) => {
    listEl.innerHTML = `<p class="empty-note">Could not reach the backend at ${REPLAYS_URL}: ${err.message}</p>`;
  });
