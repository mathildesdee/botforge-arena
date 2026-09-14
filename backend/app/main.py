import asyncio
import logging
import time

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import db
from .lobby import Lobby
from .match import DEFAULT_NUM_ROUNDS, DEFAULT_ROUND_TIME_LIMIT, Match
from .replay import Recorder
from .robot import Robot
from .tournament import Participant, Tournament
from .validation import validate_robot_json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("botforge.main")

TICK_RATE = 20  # ticks per second
DT = 1 / TICK_RATE

app = FastAPI(title="BotForge Arena")

# The frontend is a separate static site (different origin/port from
# this server in dev — see frontend/src/config.js), so plain browser
# fetch() calls to /api/robots/validate and /api/leaderboard need CORS
# enabled or the browser silently blocks them (curl doesn't enforce
# CORS, so this was easy to miss testing with curl alone). WebSocket
# connections (/ws) aren't subject to CORS, so this only matters for
# the two REST endpoints.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

db.init_db()

lobby = Lobby()
activity_in_progress = False  # a match or tournament currently owns the arena

MAX_SIMULATE_ROUNDS = 2000


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


@app.get("/api/replays")
def replays():
    """Lightweight index of recorded rounds (PDF section 28) — enough
    for a browser to list past matches before fetching a full one."""
    return db.list_replays()


@app.get("/api/replays/{round_result_id}")
def replay(round_result_id: int):
    """The full tick-by-tick recording for one round, plus its notable-
    moment markers (first shot/hit, health thresholds, final kill)."""
    recording = db.get_replay(round_result_id)
    if recording is None:
        return {"found": False}
    return {"found": True, **recording}


class SimulateRequest(BaseModel):
    robot_a: dict
    robot_b: dict
    rounds: int = 100


@app.post("/api/simulate")
async def simulate(request: SimulateRequest):
    """Fast headless simulation (PDF section 29, "Simulation mode"):
    plays many rounds between two robot definitions with no real-time
    pacing and no live broadcast, and reports a win/draw tally — so a
    player can compare two robot versions statistically instead of
    watching each one play out live. Stateless: nothing is persisted."""
    for label, robot_definition in (("robot_a", request.robot_a), ("robot_b", request.robot_b)):
        is_valid, errors = validate_robot_json(robot_definition)
        if not is_valid:
            return {"valid": False, "field": label, "errors": errors}

    rounds = max(1, min(request.rounds, MAX_SIMULATE_ROUNDS))
    robots = [
        Robot("robot_a", request.robot_a["name"], x=0, y=0, direction=0,
              build=request.robot_a["build"], logic=request.robot_a["logic"],
              variables=request.robot_a.get("variables"), behaviours=request.robot_a.get("behaviours")),
        Robot("robot_b", request.robot_b["name"], x=0, y=0, direction=0,
              build=request.robot_b["build"], logic=request.robot_b["logic"],
              variables=request.robot_b.get("variables"), behaviours=request.robot_b.get("behaviours")),
    ]
    match = Match(robots, num_rounds=rounds, round_time_limit=DEFAULT_ROUND_TIME_LIMIT)
    await asyncio.to_thread(match.run_to_completion, DT)

    counts = match.round_win_counts()
    return {
        "valid": True,
        "rounds_played": len(match.round_results),
        "wins": {"robot_a": counts["robot_a"], "robot_b": counts["robot_b"]},
        "draws": counts["draws"],
    }


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
    global activity_in_progress

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
        if activity_in_progress:
            await _send(player, {"type": "lobby_error", "message": "A match or tournament is already running."})
            return
        if not lobby.can_start_match():
            await _send(player, {
                "type": "lobby_error",
                "message": "Need 2-8 ready players (with an uploaded robot each) to start.",
            })
            return
        activity_in_progress = True
        asyncio.create_task(_run_match(lobby.ready_players()))
        return  # _run_match broadcasts its own state; nothing more to do here

    elif msg_type == "start_tournament":
        if activity_in_progress:
            await _send(player, {"type": "lobby_error", "message": "A match or tournament is already running."})
            return
        if len(lobby.ready_players()) < 2:
            await _send(player, {
                "type": "lobby_error",
                "message": "Need at least 2 ready players (with an uploaded robot each) to start a tournament.",
            })
            return
        activity_in_progress = True
        asyncio.create_task(_run_tournament(lobby.ready_players()))
        return  # _run_tournament broadcasts its own state; nothing more to do here

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
    # Snapshot the keys before iterating: awaiting send_json() below
    # yields control to the event loop, and a concurrent disconnect's
    # WebSocketDisconnect handler calls lobby.remove_player() (mutating
    # this same dict) before this loop resumes — iterating the live
    # dict directly crashes with "dictionary changed size during
    # iteration" the instant that happens mid-match.
    for websocket in list(lobby.players):
        try:
            await websocket.send_json(message)
        except Exception:
            stale.append(websocket)
    for websocket in stale:
        lobby.remove_player(websocket)


async def _play_match(match, match_id, robot_version_lookup):
    """Runs `match` to completion, persisting round results/stats and
    broadcasting game_state plus match_start/round_start/round_end/
    match_end. Shared by the single-match and tournament flows."""
    await _broadcast({"type": "match_start", "total_rounds": match.num_rounds})

    while not match.finished:
        match.start_round()
        await _broadcast({
            "type": "round_start",
            "round": match.current_round,
            "total_rounds": match.num_rounds,
        })

        recorder = Recorder()  # PDF section 28: one recording per round

        while True:
            start = time.perf_counter()
            result = match.tick(DT)

            state = match.arena.state(events=result["events"])
            recorder.record(state)
            await _broadcast(state)

            round_result = result["round_result"]
            if round_result is not None:
                round_result_id = db.record_round_result(match_id, round_result, robot_version_lookup)
                db.save_replay(round_result_id, recorder.to_dict())
                await _broadcast({
                    "type": "round_end",
                    "round": round_result.round_number,
                    "winner_id": round_result.winner_id,
                    "scores": dict(match.scores),
                    "replay_id": round_result_id,
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


async def _run_match(ready_players):
    """Runs one match for the players who were ready when `start_match`
    was received, broadcasting game_state and the match lifecycle
    messages to every connected client (players and spectators alike)."""
    global activity_in_progress

    try:
        robots = [
            Robot(
                robot_id=player.id,
                name=player.robot_definition["name"],
                x=0, y=0, direction=0,
                build=player.robot_definition["build"],
                logic=player.robot_definition["logic"],
                variables=player.robot_definition.get("variables"),
                behaviours=player.robot_definition.get("behaviours"),
            )
            for player in ready_players
        ]
        robot_version_lookup = {player.id: player.robot_version_id for player in ready_players}
        match_id = db.create_match(list(robot_version_lookup.values()))
        match = Match(robots, num_rounds=DEFAULT_NUM_ROUNDS, round_time_limit=DEFAULT_ROUND_TIME_LIMIT)

        await _play_match(match, match_id, robot_version_lookup)
    finally:
        activity_in_progress = False
        lobby.reset_ready_states()
        await _broadcast(lobby.state_dict())


async def _run_tournament(ready_players):
    """Milestone 10: schedules every pairing among the players who were
    ready when `start_tournament` was received, runs each pairing as a
    full match, and broadcasts a final ranking across all pairings."""
    global activity_in_progress

    try:
        participants = [
            Participant(
                player.id,
                player.robot_definition["name"],
                player.robot_definition["build"],
                player.robot_definition["logic"],
                variables=player.robot_definition.get("variables"),
                behaviours=player.robot_definition.get("behaviours"),
                robot_version_id=player.robot_version_id,
            )
            for player in ready_players
        ]
        tournament = Tournament(participants, num_rounds=DEFAULT_NUM_ROUNDS, round_time_limit=DEFAULT_ROUND_TIME_LIMIT)

        await _broadcast({
            "type": "tournament_start",
            "participants": [{"id": p.id, "name": p.name} for p in participants],
            "total_pairings": len(tournament.pairings),
        })

        while not tournament.finished:
            pairing = tournament.start_next_pairing()
            if pairing is None:
                break
            a, b = pairing
            robot_version_lookup = {a.id: a.robot_version_id, b.id: b.robot_version_id}
            match_id = db.create_match(list(robot_version_lookup.values()))

            await _broadcast({
                "type": "tournament_pairing_start",
                "pairing": tournament.current_pairing_index + 1,
                "total_pairings": len(tournament.pairings),
                "participants": [a.id, b.id],
            })

            await _play_match(tournament.current_match, match_id, robot_version_lookup)

            tournament.finish_current_pairing()
            await _broadcast({
                "type": "tournament_pairing_end",
                "pairing": tournament.current_pairing_index,
                "result": tournament.pairing_results[-1].to_dict(),
            })

        await _broadcast({"type": "tournament_end", **tournament.standings()})
    finally:
        activity_in_progress = False
        lobby.reset_ready_states()
        await _broadcast(lobby.state_dict())
