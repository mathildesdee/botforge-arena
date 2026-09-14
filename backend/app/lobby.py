"""In-memory multiplayer lobby: connected players, names, ready state,
and whether enough of them are ready to start a match.

Milestone 6 (Multiplayer Lobby) from BotForge Arena.pdf: players open
the site, choose a name, upload a robot, see other connected players,
mark themselves ready, and start a match together.

Pure state/logic, no FastAPI or WebSocket dependency, so it's
unit-testable standalone — main.py owns turning this into WS messages.
"""

import itertools

MIN_PLAYERS_TO_START = 2
MAX_PLAYERS_TO_START = 8  # "a match contains between two and eight robots" (Part A.1)
NAME_MAX_LENGTH = 24

_player_id_counter = itertools.count(1)


class Player:
    def __init__(self):
        self.id = f"player_{next(_player_id_counter)}"
        self.name = None
        self.ready = False
        self.robot_definition = None
        self.robot_version_id = None

    def display_name(self):
        return self.name or self.id

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.display_name(),
            "ready": self.ready,
            "has_robot": self.robot_definition is not None,
        }


class Lobby:
    """`connection_key` is whatever the caller uses to identify a
    connection (e.g. a WebSocket instance) — the lobby only ever uses
    it as a dict key, never inspects it."""

    def __init__(self):
        self.players = {}

    def add_player(self, connection_key):
        player = Player()
        self.players[connection_key] = player
        return player

    def remove_player(self, connection_key):
        self.players.pop(connection_key, None)

    def set_name(self, player, name):
        name = (name or "").strip()[:NAME_MAX_LENGTH]
        player.name = name or None

    def set_robot(self, player, robot_definition, robot_version_id):
        player.robot_definition = robot_definition
        player.robot_version_id = robot_version_id
        player.ready = False  # re-uploading a robot means re-confirming readiness

    def set_ready(self, player, ready):
        player.ready = bool(ready) and player.robot_definition is not None

    def ready_players(self):
        return [p for p in self.players.values() if p.ready]

    def can_start_match(self):
        count = len(self.ready_players())
        return MIN_PLAYERS_TO_START <= count <= MAX_PLAYERS_TO_START

    def reset_ready_states(self):
        for player in self.players.values():
            player.ready = False

    def state_dict(self):
        return {
            "type": "lobby_state",
            "players": [p.to_dict() for p in self.players.values()],
        }
