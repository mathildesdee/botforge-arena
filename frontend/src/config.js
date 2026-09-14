// Update these once the real backend endpoints exist. Until then they
// point at the local dev-tools/ stub servers.

// See "[Backend] Game loop + WebSocket server" issue.
export const WS_URL = 'ws://localhost:8765/ws';

// See docs/ARCHITECTURE.md #6 and the "[Backend] Robot JSON schema
// validation" issue.
export const VALIDATE_URL = 'http://localhost:8766/api/robots/validate';

// See docs/ARCHITECTURE.md #3 (multiplayer lobby protocol) and the
// "[Frontend] Multiplayer lobby" issue.
export const LOBBY_WS_URL = 'ws://localhost:8767/lobby';
