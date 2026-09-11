// Shared visual "robot card": a bar-chart preview of a build's stat
// distribution (docs/ARCHITECTURE.md #2). Used by both the builder
// page (live preview while allocating points) and the upload page
// (preview of an uploaded robot's stats).

export const BUILD_STATS = [
  { key: 'speed', label: 'Speed' },
  { key: 'armor', label: 'Armor' },
  { key: 'weapon_power', label: 'Weapon Power' },
  { key: 'accuracy', label: 'Accuracy' },
  { key: 'fire_rate', label: 'Fire Rate' },
  { key: 'sensor_range', label: 'Sensor Range' },
];

export function renderRobotCard(container, title, build) {
  const maxStat = Math.max(1, ...Object.values(build));
  container.innerHTML = `<h3>${title}</h3>`;

  BUILD_STATS.forEach((stat) => {
    const value = build[stat.key] ?? 0;
    const row = document.createElement('div');
    row.className = 'card-bar-row';

    const label = document.createElement('span');
    label.textContent = stat.label;

    const track = document.createElement('div');
    track.className = 'card-bar-track';
    const fill = document.createElement('div');
    fill.className = 'card-bar-fill';
    fill.style.width = `${(value / maxStat) * 100}%`;
    track.appendChild(fill);

    const valueEl = document.createElement('span');
    valueEl.textContent = value;

    row.append(label, track, valueEl);
    container.appendChild(row);
  });
}
