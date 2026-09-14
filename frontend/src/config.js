// Points at the real backend (see backend/app/main.py). Run it with
// `uvicorn app.main:app --port 8000` from backend/, or update these
// if it's running elsewhere.

// Every connection to /ws is simultaneously a lobby member and a
// match spectator — see docs/ARCHITECTURE.md #1-#4. The arena page
// and the lobby page both connect here.
export const WS_URL = 'ws://localhost:8000/ws';

// See docs/ARCHITECTURE.md #7.
export const VALIDATE_URL = 'http://localhost:8000/api/robots/validate';

// See docs/ARCHITECTURE.md #8.
export const LEADERBOARD_URL = 'http://localhost:8000/api/leaderboard';

// See docs/ARCHITECTURE.md #9. Append '/<round_result_id>' for one
// full recording.
export const REPLAYS_URL = 'http://localhost:8000/api/replays';
