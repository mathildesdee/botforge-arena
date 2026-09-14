// sessionStorage key bridging practice.html (where a build is picked) to
// PracticeScene.js (which reads it once, when the Phaser game is created,
// to send as the /ws/practice init message). sessionStorage rather than
// localStorage since a practice pick is throwaway, like the session itself.
export const PRACTICE_BUILD_KEY = 'botforge:practice-build';
