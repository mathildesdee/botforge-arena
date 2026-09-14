// Multiplayer lobby (Milestone 6): pick a name, attach a robot,
// mark ready, watch everyone else do the same, then move to
// spectating the match together. Protocol is docs/ARCHITECTURE.md #3
// — a separate WebSocket connection from the arena's game_state feed.

import JsonSocket from './net/JsonSocket.js';
import { readRobotFile } from './robotFile.js';
import { LOBBY_WS_URL } from './config.js';

const nameInput = document.getElementById('player-name');
const fileInput = document.getElementById('robot-file');
const robotSummaryEl = document.getElementById('robot-summary');
const joinButton = document.getElementById('join-button');
const joinErrorEl = document.getElementById('join-error');
const joinFormEl = document.getElementById('join-form');

const lobbyRoomEl = document.getElementById('lobby-room');
const lobbyStatusEl = document.getElementById('lobby-status');
const readyButton = document.getElementById('ready-button');
const leaveButton = document.getElementById('leave-button');
const playersEl = document.getElementById('lobby-players');

let selectedRobot = null;
let socket = null;
let myPlayerId = null;
let isReady = false;
let hasJoined = false;

function refreshJoinButton() {
  joinButton.disabled = !nameInput.value.trim() || !selectedRobot;
}

fileInput.addEventListener('change', async () => {
  const file = fileInput.files[0];
  if (!file) return;

  try {
    const robot = await readRobotFile(file);
    if (!robot.name) {
      throw new Error('missing "name" field');
    }
    selectedRobot = robot;
    robotSummaryEl.textContent = `"${robot.name}" selected.`;
  } catch (err) {
    selectedRobot = null;
    robotSummaryEl.textContent = `Could not use this file: ${err.message}`;
  }
  refreshJoinButton();
});

nameInput.addEventListener('input', refreshJoinButton);

function renderPlayers(players) {
  playersEl.innerHTML = '';
  players.forEach((player) => {
    const row = document.createElement('div');
    row.className = 'lobby-player';

    const info = document.createElement('div');
    const you = player.id === myPlayerId ? ' (you)' : '';
    info.innerHTML = `<strong>${player.name}${you}</strong><br><span class="lobby-player-robot">${player.robot_name}</span>`;

    const badge = document.createElement('span');
    badge.className = `ready-badge${player.ready ? ' is-ready' : ''}`;
    badge.textContent = player.ready ? 'Ready' : 'Not ready';

    row.append(info, badge);
    playersEl.appendChild(row);

    if (player.id === myPlayerId) {
      isReady = player.ready;
      readyButton.textContent = isReady ? 'Cancel ready' : 'Mark ready';
    }
  });
}

function handleMessage(message) {
  switch (message.type) {
    case 'joined':
      myPlayerId = message.id;
      break;
    case 'lobby_state':
      renderPlayers(message.players);
      lobbyStatusEl.textContent = `${message.players.length} player(s) in lobby. Waiting for everyone to be ready (minimum 2 players).`;
      break;
    case 'match_starting':
      lobbyStatusEl.innerHTML = `Match starting in ${message.countdown}s — <a href="index.html">go watch in the Arena</a>.`;
      readyButton.disabled = true;
      leaveButton.disabled = true;
      break;
    default:
      break;
  }
}

joinButton.addEventListener('click', () => {
  joinErrorEl.textContent = '';
  socket = new JsonSocket(LOBBY_WS_URL, {
    onMessage: handleMessage,
    onStatusChange: (status) => {
      if (status === 'connected' && !hasJoined) {
        hasJoined = true;
        socket.send({
          type: 'join',
          name: nameInput.value.trim(),
          robot_name: selectedRobot.name,
        });
        joinFormEl.hidden = true;
        lobbyRoomEl.hidden = false;
        lobbyStatusEl.textContent = `Connected as ${nameInput.value.trim()}.`;
      } else if (status === 'error' || status === 'disconnected') {
        if (!hasJoined) {
          joinErrorEl.textContent = `Could not reach the lobby server at ${LOBBY_WS_URL}. Is it running?`;
        } else {
          lobbyStatusEl.textContent = 'Disconnected from lobby — retrying…';
        }
      }
    },
  });
  socket.connect();
});

readyButton.addEventListener('click', () => {
  socket.send({ type: 'set_ready', ready: !isReady });
});

leaveButton.addEventListener('click', () => {
  socket.send({ type: 'leave' });
  socket.disconnect();
  socket = null;
  hasJoined = false;
  myPlayerId = null;
  joinFormEl.hidden = false;
  lobbyRoomEl.hidden = true;
  readyButton.disabled = false;
  leaveButton.disabled = false;
});
