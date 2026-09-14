// Points at the real backend (see backend/app/main.py). Run it with
// `uvicorn app.main:app --port 8000` from backend/, or update these
// if it's running elsewhere.

// Every connection to /ws is simultaneously a lobby member and a
// match spectator — see docs/ARCHITECTURE.md #1-#3. The arena page
// and the lobby page both connect here.
export const WS_URL = 'ws://localhost:8000/ws';

// See docs/ARCHITECTURE.md #6.
export const VALIDATE_URL = 'http://localhost:8000/api/robots/validate';

// A real GET /api/leaderboard now exists too (docs/ARCHITECTURE.md #7)
// but leaderboard.js still reads static mock data — wiring it up is
// Milestone 8 work, not part of this lobby pass.
