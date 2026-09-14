import asyncio
import logging
import time

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from . import db
from .lobby import Lobby
from .match import DEFAULT_NUM_ROUNDS, DEFAULT_ROUND_TIME_LIMIT, Match
from .robot import Robot
from .validation import validate_robot_json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("botforge.main")

TICK_RATE = 20  # ticks per second
DT = 1 / TICK_RATE

app = FastAPI(title="BotForge Arena")
db.init_db()

lobby = Lobby()
match_in_progress = False


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
    """Milestone 6 (Multiplayer Lobby): players connect here, join with a
    name, upload a robot, ready up, and start a match together — everyone
    else connected watches live (`spectate together`)."""
    await websocket.accept()
    player = lobby.add_player(websocket)
    await _broadcast(lobby.state_dict())

    try:
        while True:
            try:
                message = await websocket.receive_json()
            except ValueError:
                continue  # malformed JSON from this client — ignore, stay connected
            await _handle_client_message(player, message)
    except WebSocketDisconnect:
        lobby.remove_player(websocket)
        await _broadcast(lobby.state_dict())


async def _handle_client_message(player, message):
    global match_in_progress

    if not isinstance(message, dict):
        return
    msg_type = message.get("type")

    if msg_type == "join":
        lobby.set_name(player, message.get("name"))

    elif msg_type == "upload_robot":
        is_valid, errors = validate_robot_json(message.get("robot"))
        if not is_valid:
            await _send(player, {"type": "robot_upload_result", "valid": False, "errors": errors})
            return
        robot_definition = message["robot"]
        _, _, version_id = db.save_robot_version(player.display_name(), robot_definition)
        lobby.set_robot(player, robot_definition, version_id)
        await _send(player, {"type": "robot_upload_result", "valid": True, "robot": robot_definition})

    elif msg_type == "set_ready":
        lobby.set_ready(player, message.get("ready"))

    elif msg_type == "start_match":
        if match_in_progress:
            await _send(player, {"type": "lobby_error", "message": "A match is already running."})
            return
        if not lobby.can_start_match():
            await _send(player, {
                "type": "lobby_error",
                "message": "Need 2-8 ready players (with an uploaded robot each) to start.",
            })
            return
        match_in_progress = True
        asyncio.create_task(_run_match(lobby.ready_players()))
        return  # _run_match broadcasts its own state; nothing more to do here

    else:
        return  # unrecognized message type — ignore

    await _broadcast(lobby.state_dict())


def _find_websocket(player):
    for websocket, candidate in lobby.players.items():
        if candidate is player:
            return websocket
    return None


async def _send(player, message):
    websocket = _find_websocket(player)
    if websocket is None:
        return
    try:
        await websocket.send_json(message)
    except Exception:
        pass


async def _broadcast(message):
    stale = []
    for websocket in lobby.players:
        try:
            await websocket.send_json(message)
        except Exception:
            stale.append(websocket)
    for websocket in stale:
        lobby.remove_player(websocket)


async def _run_match(ready_players):
    """Runs one match for the players who were ready when `start_match`
    was received, broadcasting game_state and the match lifecycle
    messages to every connected client (players and spectators alike)."""
    global match_in_progress

    try:
        robots = [
            Robot(
                robot_id=player.id,
                name=player.robot_definition["name"],
                x=0, y=0, direction=0,
                build=player.robot_definition["build"],
                logic=player.robot_definition["logic"],
            )
            for player in ready_players
        ]
        robot_version_lookup = {player.id: player.robot_version_id for player in ready_players}
        match_id = db.create_match(list(robot_version_lookup.values()))
        match = Match(robots, num_rounds=DEFAULT_NUM_ROUNDS, round_time_limit=DEFAULT_ROUND_TIME_LIMIT)

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
    finally:
        match_in_progress = False
        lobby.reset_ready_states()
        await _broadcast(lobby.state_dict())
