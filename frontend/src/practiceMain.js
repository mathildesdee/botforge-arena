// Bootstraps practice.html: lets the player pick one of their saved
// builds (from builder.html), then creates the Phaser game once they
// click Start — PracticeScene.js reads the chosen build back out of
// sessionStorage when it connects.

import PracticeScene from './scenes/PracticeScene.js';
import { loadSavedRobots } from './savedRobotsStorage.js';
import { PRACTICE_BUILD_KEY } from './practiceStorage.js';

const select = document.getElementById('practice-robot-select');
const startButton = document.getElementById('practice-start-button');

const savedRobots = loadSavedRobots();
savedRobots.forEach((robot, index) => {
  const option = document.createElement('option');
  option.value = String(index);
  option.textContent = `${robot.name} (by ${robot.creator || 'unknown'})`;
  select.appendChild(option);
});

let started = false;

startButton.addEventListener('click', () => {
  if (started) return;
  started = true;

  const chosen = select.value === '' ? null : savedRobots[Number(select.value)];
  try {
    if (chosen) sessionStorage.setItem(PRACTICE_BUILD_KEY, JSON.stringify(chosen.build));
    else sessionStorage.removeItem(PRACTICE_BUILD_KEY);
  } catch {
    // sessionStorage unavailable — PracticeScene falls back to the server's default build.
  }

  select.disabled = true;
  startButton.disabled = true;
  startButton.textContent = 'Practicing…';

  new Phaser.Game({
    type: Phaser.AUTO,
    width: 800,
    height: 600,
    parent: 'arena',
    backgroundColor: '#0b0e13',
    scene: [PracticeScene],
  });
});
