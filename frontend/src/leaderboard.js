// Renders leaderboard entries matching docs/ARCHITECTURE.md #6.
// Source is static mock JSON today; swapping in a real
// `/api/leaderboard` fetch later is a one-line change here since the
// row shape is already agreed with the backend persistence layer.

const MOCK_LEADERBOARD_URL = 'src/mock/leaderboard.mock.json';

const tbody = document.getElementById('leaderboard-body');

function formatPct(value) {
  return `${Math.round(value * 100)}%`;
}

function renderRows(entries) {
  tbody.innerHTML = '';
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

fetch(MOCK_LEADERBOARD_URL)
  .then((response) => response.json())
  .then(renderRows)
  .catch((err) => {
    tbody.innerHTML = `<tr><td colspan="10">Could not load leaderboard data: ${err.message}</td></tr>`;
  });
