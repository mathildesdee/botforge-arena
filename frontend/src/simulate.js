// Simulation mode (docs/ARCHITECTURE.md #10, PDF section 29): run two
// robots against each other many times, headlessly, and report a
// win/draw tally — "is my robot smarter now?" without watching every
// round play out. Each side is picked from this browser's saved
// robots (built via builder.html) or an uploaded file.

import { readRobotFile } from './robotFile.js';
import { loadSavedRobots } from './savedRobotsStorage.js';
import { SIMULATE_URL } from './config.js';

const MAX_ROUNDS = 2000;

const selectEls = {
  a: document.getElementById('robot-a-select'),
  b: document.getElementById('robot-b-select'),
};
const fileEls = {
  a: document.getElementById('robot-a-file'),
  b: document.getElementById('robot-b-file'),
};
const summaryEls = {
  a: document.getElementById('robot-a-summary'),
  b: document.getElementById('robot-b-summary'),
};
const roundsInput = document.getElementById('rounds-input');
const runButton = document.getElementById('run-button');
const resultEl = document.getElementById('sim-result');

const robots = { a: null, b: null };

function populateSelect(select, savedRobots) {
  savedRobots.forEach((robot, index) => {
    const option = document.createElement('option');
    option.value = String(index);
    option.textContent = `${robot.name} (by ${robot.creator || 'unknown'})`;
    select.appendChild(option);
  });
}

function refreshRunButton() {
  runButton.disabled = !robots.a || !robots.b;
}

function setSlot(slot, robot, sourceLabel) {
  robots[slot] = robot;
  summaryEls[slot].textContent = robot ? `Using "${robot.name}" (${sourceLabel}).` : 'No robot selected.';
  refreshRunButton();
}

['a', 'b'].forEach((slot) => {
  const savedRobots = loadSavedRobots();
  populateSelect(selectEls[slot], savedRobots);

  selectEls[slot].addEventListener('change', () => {
    if (selectEls[slot].value === '') {
      setSlot(slot, null);
      return;
    }
    fileEls[slot].value = '';
    setSlot(slot, savedRobots[Number(selectEls[slot].value)], 'saved');
  });

  fileEls[slot].addEventListener('change', async () => {
    const file = fileEls[slot].files[0];
    if (!file) return;
    try {
      const robot = await readRobotFile(file);
      selectEls[slot].value = '';
      setSlot(slot, robot, 'uploaded file');
    } catch (err) {
      setSlot(slot, null);
      summaryEls[slot].textContent = `Could not parse this file as JSON: ${err.message}`;
    }
  });
});

function renderBanner(kind, message) {
  const banner = document.createElement('div');
  banner.className = `banner ${kind}`;
  banner.textContent = message;
  resultEl.appendChild(banner);
  return banner;
}

function renderResult(payload) {
  resultEl.innerHTML = '';
  renderBanner('success', `Ran ${payload.rounds_played} round(s).`);

  const total = payload.rounds_played || 1;
  const winsA = payload.wins.robot_a;
  const winsB = payload.wins.robot_b;
  const draws = payload.draws;

  const viz = document.createElement('div');
  viz.className = 'viz-root';

  const bar = document.createElement('div');
  bar.className = 'sim-bar';
  [
    { count: winsA, color: 'var(--series-a)' },
    { count: winsB, color: 'var(--series-b)' },
    { count: draws, color: 'var(--series-draw)' },
  ].forEach(({ count, color }) => {
    if (count === 0) return;
    const segment = document.createElement('div');
    segment.className = 'sim-bar-segment';
    segment.style.width = `${(count / total) * 100}%`;
    segment.style.background = color;
    bar.appendChild(segment);
  });
  viz.appendChild(bar);

  const legend = document.createElement('div');
  legend.className = 'sim-legend';
  [
    { label: robots.a?.name || 'Robot A', count: winsA, color: 'var(--series-a)' },
    { label: robots.b?.name || 'Robot B', count: winsB, color: 'var(--series-b)' },
    { label: 'Draws', count: draws, color: 'var(--series-draw)' },
  ].forEach(({ label, count, color }) => {
    const item = document.createElement('div');
    item.className = 'sim-legend-item';
    const pct = Math.round((count / total) * 100);
    item.innerHTML = `<span class="sim-legend-swatch" style="background:${color}"></span>${label}: ${count} (${pct}%)`;
    legend.appendChild(item);
  });
  viz.appendChild(legend);

  resultEl.appendChild(viz);
}

function renderValidationErrors(payload) {
  resultEl.innerHTML = '';
  const banner = renderBanner('error', `"${payload.field}" was rejected:`);
  const list = document.createElement('ul');
  list.className = 'error-list';
  (payload.errors || []).forEach((err) => {
    const item = document.createElement('li');
    item.className = 'error-item';
    item.innerHTML = `<code>${err.field ?? '(general)'}</code> — ${err.message}`;
    list.appendChild(item);
  });
  banner.appendChild(list);
}

runButton.addEventListener('click', async () => {
  resultEl.innerHTML = '';
  runButton.disabled = true;
  runButton.textContent = 'Running…';

  const rounds = Math.max(1, Math.min(Number(roundsInput.value) || 100, MAX_ROUNDS));

  try {
    const response = await fetch(SIMULATE_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ robot_a: robots.a, robot_b: robots.b, rounds }),
    });
    const payload = await response.json();
    if (payload.valid) {
      renderResult(payload);
    } else {
      renderValidationErrors(payload);
    }
  } catch (err) {
    resultEl.innerHTML = '';
    renderBanner('error', `Could not reach the backend at ${SIMULATE_URL}: ${err.message}`);
  } finally {
    runButton.disabled = false;
    runButton.textContent = 'Run simulation';
    refreshRunButton();
  }
});
