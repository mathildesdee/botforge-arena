// Thin wrapper around the browser WebSocket API for the game_state
// protocol in docs/ARCHITECTURE.md. Reconnects automatically on drop,
// and only forwards messages of type "game_state" — other envelope
// types (match_start, round_end, etc.) can be handled here later
// without touching the scenes that consume game state.

const RECONNECT_DELAY_MS = 2000;

export default class GameSocket {
  constructor(url, { onGameState, onStatusChange } = {}) {
    this.url = url;
    this.onGameState = onGameState || (() => {});
    this.onStatusChange = onStatusChange || (() => {});
    this.socket = null;
    this.shouldReconnect = false;
  }

  connect() {
    this.shouldReconnect = true;
    this.open();
  }

  open() {
    this.onStatusChange('connecting');
    this.socket = new WebSocket(this.url);

    this.socket.addEventListener('open', () => this.onStatusChange('connected'));

    this.socket.addEventListener('message', (event) => {
      let message;
      try {
        message = JSON.parse(event.data);
      } catch (err) {
        console.error('GameSocket: received non-JSON message', err);
        return;
      }
      if (message.type === 'game_state') {
        this.onGameState(message);
      }
    });

    this.socket.addEventListener('close', () => {
      this.onStatusChange('disconnected');
      if (this.shouldReconnect) {
        setTimeout(() => this.open(), RECONNECT_DELAY_MS);
      }
    });

    this.socket.addEventListener('error', () => {
      this.onStatusChange('error');
    });
  }

  disconnect() {
    this.shouldReconnect = false;
    this.socket?.close();
  }
}
