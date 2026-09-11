import asyncio
import logging
import time

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from . import db
from .match import DEFAULT_NUM_ROUNDS, DEFAULT_ROUND_TIME_LIMIT, Match
from .robot import Robot
from .sample_robots import SAMPLE_ROBOTS
from .validation import validate_robot_json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("botforge.main")

TICK_RATE = 20  # ticks per second
DT = 1 / TICK_RATE

app = FastAPI(title="BotForge Arena")
db.init_db()

connected_clients: set[WebSocket] = set()

# {sample robot name: robot_version_id}, registered once at startup so the
# demo loop doesn't spam a new robot_versions row every match.
_sample_version_ids: dict[str, int] = {}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/robots/validate")
def validate_robot(robot: dict):
    """Validates an uploaded robot program (docs/ARCHITECTURE.md #3-#4).
    Contract: frontend/src/upload.js posts the raw robot JSON here and
    expects {"valid": true, "robot": ...} or {"valid": false, "errors": [...]}."""
    is_valid, errors = validate_robot_json(robot)
    if not is_valid:
        return {"valid": False, "errors": errors}
    return {"valid": True, "robot": robot}


@app.get("/api/leaderboard")
def leaderboard():
    return db.get_leaderboard()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.add(websocket)
    try:
        while True:
            # No client input yet — the server pushes state, the browser only renders it.
            await websocket.receive_text()
    except WebSocketDisconnect:
        connected_clients.discard(websocket)


async def _broadcast(message):
    stale = []
    for client in connected_clients:
        try:
            await client.send_json(message)
        except Exception:
            stale.append(client)
    for client in stale:
        connected_clients.discard(client)


def _ensure_sample_robot_versions():
    """Registers each built-in demo robot as a robot_version exactly once
    so repeated demo matches reuse the same DB rows instead of creating a
    fresh version every loop iteration."""
    for definition in SAMPLE_ROBOTS:
        name = definition["name"]
        if name in _sample_version_ids:
            continue
        is_valid, errors = validate_robot_json(definition)
        if not is_valid:
            raise RuntimeError(f"Invalid sample robot {name}: {errors}")
        _, _, version_id = db.save_robot_version(definition["creator"], definition)
        _sample_version_ids[name] = version_id


def _build_demo_match():
    """Builds a Match from the built-in sample robots so the server has a
    playable demo even before any real robot has been uploaded."""
    robots = [
        Robot(
            robot_id=f"robot_{i + 1}",
            name=definition["name"],
            x=0, y=0, direction=0,
            build=definition["build"],
            logic=definition["logic"],
        )
        for i, definition in enumerate(SAMPLE_ROBOTS)
    ]
    robot_version_lookup = {
        robot.id: _sample_version_ids[definition["name"]]
        for robot, definition in zip(robots, SAMPLE_ROBOTS)
    }
    match_id = db.create_match(list(robot_version_lookup.values()))
    return Match(robots, num_rounds=DEFAULT_NUM_ROUNDS, round_time_limit=DEFAULT_ROUND_TIME_LIMIT), \
        robot_version_lookup, match_id


async def game_loop():
    """Runs demo matches back-to-back, broadcasting `game_state` every tick
    plus the match_start/round_start/round_end/match_end lifecycle messages
    the frontend already consumes (see frontend/src/scenes/ArenaScene.js
    and frontend/dev-tools/mock_ws_server.py)."""
    _ensure_sample_robot_versions()

    while True:
        match, robot_version_lookup, match_id = _build_demo_match()

        await _broadcast({"type": "match_start", "total_rounds": match.num_rounds})

        while not match.finished:
            match.start_round()
            await _broadcast({
                "type": "round_start",
                "round": match.current_round,
                "total_rounds": match.num_rounds,
            })

            while True:
                start = time.perf_counter()
                result = match.tick(DT)

                await _broadcast(match.arena.state(events=result["events"]))

                round_result = result["round_result"]
                if round_result is not None:
                    db.record_round_result(match_id, round_result, robot_version_lookup)
                    await _broadcast({
                        "type": "round_end",
                        "round": round_result.round_number,
                        "winner_id": round_result.winner_id,
                        "scores": dict(match.scores),
                    })
                    break

                elapsed = time.perf_counter() - start
                await asyncio.sleep(max(0.0, DT - elapsed))

        db.record_match_stats(match_id, robot_version_lookup, match.arena.robots)
        db.finish_match(match_id)

        ranking = match.final_result()["ranking"]
        winner_id = ranking[0]["robot_id"] if ranking else None
        await _broadcast({
            "type": "match_end",
            "winner_id": winner_id,
            "final_scores": dict(match.scores),
        })
        await asyncio.sleep(3.0)


@app.on_event("startup")
async def start_game_loop():
    asyncio.create_task(game_loop())
