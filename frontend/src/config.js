// Points at the real backend (see backend/app/main.py). Run it with
// `uvicorn app.main:app --host 0.0.0.0 --port 8000` from backend/.
//
// Derived from `location.hostname` rather than a hard-coded
// "localhost", so the exact same build works both for local testing
// and for the project brief's LAN setup ("one computer acts as the
// server, others open it in their browsers") — whoever opens
// http://<host>:8642/lobby.html gets a frontend that correctly talks
// back to the backend on that same <host>, whether that's
// "localhost", "127.0.0.1", or a real LAN IP like "192.168.1.42".
// Update BACKEND_PORT below if the backend runs on a different port.
const BACKEND_HOST = location.hostname;
const BACKEND_PORT = 8000;
const WS_PROTOCOL = location.protocol === 'https:' ? 'wss' : 'ws';

// Every connection to /ws is simultaneously a lobby member and a
// match spectator — see docs/ARCHITECTURE.md #1-#4. The arena page
// and the lobby page both connect here.
export const WS_URL = `${WS_PROTOCOL}://${BACKEND_HOST}:${BACKEND_PORT}/ws`;

// See docs/ARCHITECTURE.md #7.
export const VALIDATE_URL = `http://${BACKEND_HOST}:${BACKEND_PORT}/api/robots/validate`;

// See docs/ARCHITECTURE.md #8.
export const LEADERBOARD_URL = `http://${BACKEND_HOST}:${BACKEND_PORT}/api/leaderboard`;

// See docs/ARCHITECTURE.md #9. Append '/<round_result_id>' for one
// full recording.
export const REPLAYS_URL = `http://${BACKEND_HOST}:${BACKEND_PORT}/api/replays`;

// See docs/ARCHITECTURE.md #10.
export const SIMULATE_URL = `http://${BACKEND_HOST}:${BACKEND_PORT}/api/simulate`;
