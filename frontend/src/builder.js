// Robot builder: name + 100-point stat allocator (docs/ARCHITECTURE.md #2).
// Validation here is client-side only, to give instant feedback — the
// server still re-validates on upload (separate backend issue), since
// the server is always the source of truth for whether a robot is legal.

import { BUILD_STATS as STATS, renderRobotCard } from './robotCard.js';

const TOTAL_BUILD_POINTS = 100;
const STORAGE_KEY = 'botforge:saved-robots';
const CREATOR_STORAGE_KEY = 'botforge:creator-name';

// This page only lets a player allocate build points — there's no
// logic editor yet (that's Milestone 5, a separate feature). The
// real backend validator requires `version` and `logic` on every
// robot regardless, so every robot built here ships with this
// baseline behaviour (find an enemy, close in, shoot) rather than
// failing validation or sitting inert in the arena. Matches the
// "start simple" example from the project brief.
const DEFAULT_VERSION = 1;
const DEFAULT_LOGIC = [
  { priority: 1, if: { op: 'lt', left: 'enemy.distance', right: 250 }, then: 'shoot' },
  { priority: 2, if: { op: 'lt', left: 'enemy.distance', right: 999999 }, then: 'move_toward_enemy' },
];

const form = document.getElementById('robot-form');
const nameInput = document.getElementById('robot-name');
const creatorInput = document.getElementById('creator-name');
const pointsRemainingEl = document.getElementById('points-remaining');
const robotCardEl = document.getElementById('robot-card');
const savedListEl = document.getElementById('saved-robots-list');
const saveButton = document.getElementById('save-button');
const downloadButton = document.getElementById('download-button');

const sliders = STATS.map((stat) => document.getElementById(`stat-${stat.key}`));

function currentBuild() {
  const build = {};
  STATS.forEach((stat, i) => {
    build[stat.key] = Number(sliders[i].value);
  });
  return build;
}

function totalPoints(build) {
  return Object.values(build).reduce((sum, v) => sum + v, 0);
}

function buildRobotPayload(name, creator, build) {
  return { name, creator, version: DEFAULT_VERSION, build, logic: DEFAULT_LOGIC };
}

function renderPointsRemaining(total) {
  const remaining = TOTAL_BUILD_POINTS - total;
  pointsRemainingEl.textContent =
    remaining >= 0 ? `${remaining} points remaining` : `${-remaining} points over budget`;
  pointsRemainingEl.classList.toggle('over-budget', remaining < 0);
  saveButton.disabled = remaining < 0 || !nameInput.value.trim() || !creatorInput.value.trim();
}

function loadSavedRobots() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY)) || [];
  } catch {
    return [];
  }
}

function saveSavedRobots(robots) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(robots));
  } catch {
    // localStorage unavailable (private mode, etc) — saving is best-effort only.
  }
}

function renderSavedRobots() {
  const robots = loadSavedRobots();
  savedListEl.innerHTML = '';

  if (robots.length === 0) {
    savedListEl.innerHTML = '<p class="empty-note">No robots saved yet.</p>';
    return;
  }

  robots.forEach((robot, index) => {
    const item = document.createElement('div');
    item.className = 'saved-item';

    const info = document.createElement('div');
    info.innerHTML = `<strong>${robot.name}</strong><br><span class="saved-meta">by ${
      robot.creator || 'unknown'
    } — ${totalPoints(robot.build)} / ${TOTAL_BUILD_POINTS} points used</span>`;

    const actions = document.createElement('div');
    actions.className = 'saved-actions';

    const loadBtn = document.createElement('button');
    loadBtn.type = 'button';
    loadBtn.textContent = 'Load';
    loadBtn.addEventListener('click', () => loadRobotIntoForm(robot));

    const deleteBtn = document.createElement('button');
    deleteBtn.type = 'button';
    deleteBtn.textContent = 'Delete';
    deleteBtn.addEventListener('click', () => {
      const remaining = loadSavedRobots().filter((_, i) => i !== index);
      saveSavedRobots(remaining);
      renderSavedRobots();
    });

    actions.append(loadBtn, deleteBtn);
    item.append(info, actions);
    savedListEl.appendChild(item);
  });
}

function loadRobotIntoForm(robot) {
  nameInput.value = robot.name;
  creatorInput.value = robot.creator || '';
  STATS.forEach((stat, i) => {
    sliders[i].value = robot.build[stat.key] ?? 0;
    document.getElementById(`${sliders[i].id}-value`).textContent = sliders[i].value;
  });
  refresh();
}

function refresh() {
  const build = currentBuild();
  renderPointsRemaining(totalPoints(build));
  renderRobotCard(robotCardEl, 'Preview', build);
}

sliders.forEach((slider) => {
  slider.addEventListener('input', () => {
    document.getElementById(`${slider.id}-value`).textContent = slider.value;
    refresh();
  });
});

nameInput.addEventListener('input', refresh);

creatorInput.addEventListener('input', () => {
  try {
    localStorage.setItem(CREATOR_STORAGE_KEY, creatorInput.value);
  } catch {
    // localStorage unavailable — remembering the name is best-effort only.
  }
  refresh();
});

form.addEventListener('submit', (event) => {
  event.preventDefault();
  const build = currentBuild();
  if (totalPoints(build) > TOTAL_BUILD_POINTS || !nameInput.value.trim() || !creatorInput.value.trim()) {
    return;
  }
  const robots = loadSavedRobots();
  robots.push(buildRobotPayload(nameInput.value.trim(), creatorInput.value.trim(), build));
  saveSavedRobots(robots);
  renderSavedRobots();
});

downloadButton.addEventListener('click', () => {
  const build = currentBuild();
  const robot = buildRobotPayload(
    nameInput.value.trim() || 'Unnamed Robot',
    creatorInput.value.trim() || 'Unknown',
    build
  );
  const blob = new Blob([JSON.stringify(robot, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `${robot.name.replace(/\s+/g, '_').toLowerCase()}.json`;
  link.click();
  URL.revokeObjectURL(url);
});

try {
  creatorInput.value = localStorage.getItem(CREATOR_STORAGE_KEY) || '';
} catch {
  // localStorage unavailable — the field just starts empty.
}

renderSavedRobots();
refresh();
