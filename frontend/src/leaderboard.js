// Renders leaderboard entries matching docs/ARCHITECTURE.md #8, from
// the real backend endpoint — verified against a running instance of
// backend/app/db.py's get_leaderboard(): row shape matches exactly
// (rank, robot_name, creator, matches, rounds_won, rounds_lost,
// win_pct, damage_caused, damage_received, accuracy, kills).

import { LEADERBOARD_URL } from './config.js';

const tbody = document.getElementById('leaderboard-body');

function formatPct(value) {
  return `${Math.round(value * 100)}%`;
}

function renderRows(entries) {
  tbody.innerHTML = '';

  if (entries.length === 0) {
    tbody.innerHTML = '<tr><td colspan="10">No matches played yet.</td></tr>';
    return;
  }

  entries
    .slice()
    .sort((a, b) => a.rank - b.rank)
    .forEach((entry) => {
      const row = document.createElement('tr');
      row.innerHTML = `
        <td>${entry.rank}</td>
        <td>${entry.robot_name}</td>
        <td>${entry.creator}</td>
        <td class="numeric">${entry.matches}</td>
        <td class="numeric">${entry.rounds_won}-${entry.rounds_lost}</td>
        <td class="numeric">${formatPct(entry.win_pct)}</td>
        <td class="numeric">${entry.damage_caused}</td>
        <td class="numeric">${entry.damage_received}</td>
        <td class="numeric">${formatPct(entry.accuracy)}</td>
        <td class="numeric">${entry.kills}</td>
      `;
      tbody.appendChild(row);
    });
}

fetch(LEADERBOARD_URL)
  .then((response) => {
    if (!response.ok) {
      throw new Error(`server responded ${response.status}`);
    }
    return response.json();
  })
  .then(renderRows)
  .catch((err) => {
    tbody.innerHTML = `<tr><td colspan="10">Could not reach the backend at ${LEADERBOARD_URL}: ${err.message}</td></tr>`;
  });
