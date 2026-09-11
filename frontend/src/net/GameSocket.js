// Thin wrapper around the browser WebSocket API. Reconnects
// automatically on drop and forwards every parsed message as-is —
// dispatching on `message.type` (game_state, round_start, etc, see
// docs/ARCHITECTURE.md #1-#2) is the caller's job, not this class's.

const RECONNECT_DELAY_MS = 2000;

export default class GameSocket {
  constructor(url, { onMessage, onStatusChange } = {}) {
    this.url = url;
    this.onMessage = onMessage || (() => {});
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
      this.onMessage(message);
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
