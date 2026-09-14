"""Dev-only mock lobby WebSocket server, for testing the multiplayer
lobby UI (Milestone 6, docs/ARCHITECTURE.md #3) before the real
backend lobby exists. Not the real backend — just enough state
tracking (who's joined, who's ready) to exercise the UI end to end.
Delete once the real backend implements this, or keep as a frontend
test fixture.

Usage:
    pip install -r requirements.txt
    python3 mock_lobby_server.py
"""

import asyncio
import itertools
import json

import websockets

PORT = 8767
MIN_PLAYERS_TO_START = 2

clients = {}  # websocket -> {"id": ..., "name": ..., "robot_name": ..., "ready": False}
id_counter = itertools.count(1)


def lobby_state_message():
    return json.dumps(
        {
            "type": "lobby_state",
            "players": [
                {
                    "id": p["id"],
                    "name": p["name"],
                    "robot_name": p["robot_name"],
                    "ready": p["ready"],
                }
                for p in clients.values()
                if p["name"] is not None
            ],
        }
    )


async def broadcast(message):
    # Only to sockets that have actually joined (named) — otherwise a
    # client who has connected but not yet sent "join" would receive
    # lobby_state broadcasts before its own "joined" ack, scrambling
    # the message order it expects.
    joined_sockets = [ws for ws, p in clients.items() if p["name"] is not None]
    if joined_sockets:
        await asyncio.gather(*(ws.send(message) for ws in joined_sockets), return_exceptions=True)


async def maybe_start_match():
    players = [p for p in clients.values() if p["name"] is not None]
    if len(players) >= MIN_PLAYERS_TO_START and all(p["ready"] for p in players):
        await broadcast(json.dumps({"type": "match_starting", "countdown": 3}))


async def handle(websocket):
    player = {"id": f"p{next(id_counter)}", "name": None, "robot_name": None, "ready": False}
    clients[websocket] = player

    try:
        async for raw in websocket:
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_type = msg.get("type")
            if msg_type == "join":
                player["name"] = msg.get("name") or "Player"
                player["robot_name"] = msg.get("robot_name") or "Unnamed Robot"
                await websocket.send(json.dumps({"type": "joined", "id": player["id"]}))
            elif msg_type == "set_ready":
                player["ready"] = bool(msg.get("ready"))
            elif msg_type == "leave":
                player["name"] = None
                player["ready"] = False

            await broadcast(lobby_state_message())
            await maybe_start_match()
    except websockets.ConnectionClosed:
        pass
    finally:
        clients.pop(websocket, None)
        await broadcast(lobby_state_message())


async def main():
    async with websockets.serve(handle, "localhost", PORT):
        print(f"Mock lobby server running at ws://localhost:{PORT}/lobby")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
