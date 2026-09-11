"""Dev-only mock WebSocket server for testing the frontend's live
rendering (GameSocket + ArenaScene) before the real backend WebSocket
endpoint exists. Not part of the shipped app — delete once the real
backend "Game loop + WebSocket server" issue lands, or keep it around
purely as a frontend test fixture.

Streams game_state messages (see docs/ARCHITECTURE.md #1) built from
the same fixture the static mock scene uses, animating the two robots
in a small orbit so movement is visible.

Usage:
    pip install -r requirements.txt
    python3 mock_ws_server.py
"""

import asyncio
import json
import math
import pathlib

import websockets

BASE_STATE_PATH = pathlib.Path(__file__).parent.parent / "src" / "mock" / "game_state.mock.json"
TICK_INTERVAL_SECONDS = 0.1
ORBIT_RADIUS = 40


def load_base_state():
    return json.loads(BASE_STATE_PATH.read_text())


async def stream_game_state(websocket):
    base = load_base_state()
    robots = base["robots"]
    origins = [(r["x"], r["y"]) for r in robots]
    tick = 0

    try:
        while True:
            tick += 1
            for i, robot in enumerate(robots):
                origin_x, origin_y = origins[i]
                angle = tick * 0.03 + i * math.pi
                robot["x"] = origin_x + math.cos(angle) * ORBIT_RADIUS
                robot["y"] = origin_y + math.sin(angle) * ORBIT_RADIUS
                robot["direction"] = (math.degrees(angle) + 90) % 360
                robot["health"] = max(10, 100 - (tick // 5) % 90)

            message = {
                "type": "game_state",
                "tick": tick,
                "robots": robots,
                "projectiles": base.get("projectiles", []),
                "events": [],
            }
            await websocket.send(json.dumps(message))
            await asyncio.sleep(TICK_INTERVAL_SECONDS)
    except websockets.ConnectionClosed:
        pass


async def main():
    async with websockets.serve(stream_game_state, "localhost", 8765):
        print("Mock game_state server running at ws://localhost:8765/ws")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
