// Thin, generic wrapper around the browser WebSocket API. Reconnects
// automatically on drop and forwards every parsed message as-is —
// dispatching on `message.type` is the caller's job, not this
// class's. Reused for both the arena's game_state connection and the
// lobby connection (docs/ARCHITECTURE.md #1-#3), since both are just
// "connect, exchange JSON messages, reconnect on drop".

const RECONNECT_DELAY_MS = 2000;

export default class JsonSocket {
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
        console.error('JsonSocket: received non-JSON message', err);
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

  send(message) {
    this.socket?.send(JSON.stringify(message));
  }

  disconnect() {
    this.shouldReconnect = false;
    this.socket?.close();
  }
}
