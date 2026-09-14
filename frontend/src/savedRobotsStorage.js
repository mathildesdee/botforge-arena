// Shared localStorage-backed list of robots built via builder.html.
// Used by the builder itself (to save/load) and by simulate.html (to
// populate its two robot pickers) so the key and the read/write
// logic exist in exactly one place.
export const SAVED_ROBOTS_KEY = 'botforge:saved-robots';

export function loadSavedRobots() {
  try {
    return JSON.parse(localStorage.getItem(SAVED_ROBOTS_KEY)) || [];
  } catch {
    return [];
  }
}

export function saveSavedRobots(robots) {
  try {
    localStorage.setItem(SAVED_ROBOTS_KEY, JSON.stringify(robots));
  } catch {
    // localStorage unavailable (private mode, etc) — saving is best-effort only.
  }
}
