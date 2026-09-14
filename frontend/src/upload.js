// Robot JSON upload + validation (docs/ARCHITECTURE.md #3 for the
// program shape, #4 for the validation endpoint contract). Parsing
// errors are caught client-side before ever hitting the network;
// everything else — is this a legal robot? — is decided by the
// server, since the server is always the source of truth.

import { renderRobotCard } from './robotCard.js';
import { readRobotFile } from './robotFile.js';
import { VALIDATE_URL } from './config.js';

const fileInput = document.getElementById('robot-file');
const validateButton = document.getElementById('validate-button');
const resultEl = document.getElementById('upload-result');

function renderBanner(kind, message) {
  resultEl.innerHTML = '';
  const banner = document.createElement('div');
  banner.className = `banner ${kind}`;
  banner.textContent = message;
  resultEl.appendChild(banner);
  return banner;
}

function renderValidationErrors(errors) {
  const banner = renderBanner('error', 'This robot was rejected:');
  const list = document.createElement('ul');
  list.className = 'error-list';
  errors.forEach((err) => {
    const item = document.createElement('li');
    item.className = 'error-item';
    item.innerHTML = `<code>${err.field ?? '(general)'}</code> — ${err.message}`;
    list.appendChild(item);
  });
  banner.appendChild(list);
}

function renderSuccess(robot) {
  renderBanner('success', `"${robot.name}" is a valid robot.`);
  const card = document.createElement('div');
  card.className = 'robot-card';
  resultEl.appendChild(card);
  renderRobotCard(card, 'Stats', robot.build || {});
}

async function validateSelectedFile() {
  const file = fileInput.files[0];
  if (!file) {
    renderBanner('error', 'Choose a robot JSON file first.');
    return;
  }

  let robot;
  try {
    robot = await readRobotFile(file);
  } catch (err) {
    renderBanner('error', `Could not parse this file as JSON: ${err.message}`);
    return;
  }

  let response;
  try {
    response = await fetch(VALIDATE_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(robot),
    });
  } catch (err) {
    renderBanner(
      'error',
      `Could not reach the validation server at ${VALIDATE_URL}. Is it running? (${err.message})`
    );
    return;
  }

  let payload;
  try {
    payload = await response.json();
  } catch (err) {
    renderBanner('error', `Validation server returned an unreadable response: ${err.message}`);
    return;
  }

  if (payload.valid) {
    renderSuccess(payload.robot || robot);
  } else {
    renderValidationErrors(payload.errors || [{ message: 'Unknown validation failure.' }]);
  }
}

validateButton.addEventListener('click', validateSelectedFile);
