// Multiplayer lobby (Milestone 6): pick a name, upload a robot, mark
// ready, watch everyone else do the same, then move to spectating the
// match together. Protocol is docs/ARCHITECTURE.md #3 — verified
// against the real backend (backend/app/main.py + lobby.py), not a
// mock. Notably: it's the *same* /ws connection the arena page uses,
// there's no separate "lobby endpoint", and there's no server-issued
// "this is you" id — a client recognizes its own row by the name it
// sent in `join`.

import JsonSocket from './net/JsonSocket.js';
import { renderRobotCard } from './robotCard.js';
import { readRobotFile } from './robotFile.js';
import { WS_URL } from './config.js';

const nameInput = document.getElementById('player-name');
const fileInput = document.getElementById('robot-file');
const joinButton = document.getElementById('join-button');
const joinErrorEl = document.getElementById('join-error');
const joinFormEl = document.getElementById('join-form');

const lobbyRoomEl = document.getElementById('lobby-room');
const lobbyStatusEl = document.getElementById('lobby-status');
const robotUploadResultEl = document.getElementById('robot-upload-result');
const readyButton = document.getElementById('ready-button');
const startButton = document.getElementById('start-button');
const leaveButton = document.getElementById('leave-button');
const playersEl = document.getElementById('lobby-players');

let socket = null;
let myName = null;
let hasUploadedRobot = false;
let isReady = false;

function refreshJoinButton() {
  joinButton.disabled = !nameInput.value.trim();
}

nameInput.addEventListener('input', refreshJoinButton);

function renderPlayers(players) {
  playersEl.innerHTML = '';
  players.forEach((player) => {
    const row = document.createElement('div');
    row.className = 'lobby-player';

    const you = player.name === myName ? ' (you)' : '';
    const info = document.createElement('div');
    info.innerHTML = `<strong>${player.name}${you}</strong><br><span class="lobby-player-robot">${
      player.has_robot ? 'Robot ready' : 'No robot yet'
    }</span>`;

    const badge = document.createElement('span');
    badge.className = `ready-badge${player.ready ? ' is-ready' : ''}`;
    badge.textContent = player.ready ? 'Ready' : 'Not ready';

    row.append(info, badge);
    playersEl.appendChild(row);

    if (player.name === myName) {
      isReady = player.ready;
      readyButton.textContent = isReady ? 'Cancel ready' : 'Mark ready';
      readyButton.disabled = !hasUploadedRobot;
    }
  });
}

function handleMessage(message) {
  switch (message.type) {
    case 'lobby_state':
      renderPlayers(message.players);
      break;
    case 'robot_upload_result':
      robotUploadResultEl.innerHTML = '';
      if (message.valid) {
        hasUploadedRobot = true;
        readyButton.disabled = false;
        const banner = document.createElement('div');
        banner.className = 'banner success';
        banner.textContent = `"${message.robot.name}" uploaded.`;
        robotUploadResultEl.appendChild(banner);
        const card = document.createElement('div');
        card.className = 'robot-card';
        robotUploadResultEl.appendChild(card);
        renderRobotCard(card, 'Stats', message.robot.build || {});
      } else {
        hasUploadedRobot = false;
        readyButton.disabled = true;
        const banner = document.createElement('div');
        banner.className = 'banner error';
        banner.textContent = 'This robot was rejected:';
        const list = document.createElement('ul');
        list.className = 'error-list';
        (message.errors || []).forEach((err) => {
          const item = document.createElement('li');
          item.className = 'error-item';
          item.innerHTML = `<code>${err.field ?? '(general)'}</code> — ${err.message}`;
          list.appendChild(item);
        });
        banner.appendChild(list);
        robotUploadResultEl.appendChild(banner);
      }
      break;
    case 'lobby_error':
      lobbyStatusEl.textContent = message.message;
      break;
    case 'match_start':
      lobbyStatusEl.innerHTML = `Match starting (${message.total_rounds} rounds) — <a href="index.html">go watch in the Arena</a>.`;
      readyButton.disabled = true;
      startButton.disabled = true;
      break;
    default:
      // round_start/game_state/round_end/match_end all belong to the
      // arena page once a match is running — the lobby only cares
      // about match_start as the cue to point players there.
      break;
  }
}

fileInput.addEventListener('change', async () => {
  const file = fileInput.files[0];
  if (!file || !socket) return;

  let robot;
  try {
    robot = await readRobotFile(file);
  } catch (err) {
    robotUploadResultEl.innerHTML = `<div class="banner error">Could not parse this file as JSON: ${err.message}</div>`;
    return;
  }

  // Attach the player's chosen name as the robot's creator — the
  // real validator requires it and neither the file nor the builder
  // page has a "current player" concept to supply it from elsewhere.
  socket.send({ type: 'upload_robot', robot: { ...robot, creator: myName } });
});

joinButton.addEventListener('click', () => {
  joinErrorEl.textContent = '';
  myName = nameInput.value.trim();

  socket = new JsonSocket(WS_URL, {
    onMessage: handleMessage,
    onStatusChange: (status) => {
      if (status === 'connected') {
        socket.send({ type: 'join', name: myName });
        joinFormEl.hidden = true;
        lobbyRoomEl.hidden = false;
        lobbyStatusEl.textContent = `Connected as ${myName}. Upload a robot to be able to ready up.`;
      } else if (status === 'error') {
        joinErrorEl.textContent = `Could not reach the backend at ${WS_URL}. Is it running?`;
      } else if (status === 'disconnected' && !lobbyRoomEl.hidden) {
        lobbyStatusEl.textContent = 'Disconnected — retrying…';
      }
    },
  });
  socket.connect();
});

readyButton.addEventListener('click', () => {
  socket.send({ type: 'set_ready', ready: !isReady });
});

startButton.addEventListener('click', () => {
  socket.send({ type: 'start_match' });
});

leaveButton.addEventListener('click', () => {
  // No "leave" message in the real protocol — closing the connection
  // is how the server notices you've gone.
  socket.disconnect();
  socket = null;
  myName = null;
  hasUploadedRobot = false;
  isReady = false;
  joinFormEl.hidden = false;
  lobbyRoomEl.hidden = true;
  robotUploadResultEl.innerHTML = '';
  fileInput.value = '';
  readyButton.disabled = false;
  startButton.disabled = false;
});
