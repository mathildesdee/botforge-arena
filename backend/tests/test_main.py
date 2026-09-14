"""Regression test for a real crash found while testing the frontend
replay feature: a client disconnecting mid-match used to crash the
whole match task with "RuntimeError: dictionary changed size during
iteration" -- _broadcast() iterated lobby.players directly, and the
WebSocketDisconnect handler's lobby.remove_player() call mutates that
same dict from underneath it the moment a concurrent send yields
control back to the event loop.

Uses plain asyncio.run() rather than pytest-asyncio (not a project
dependency) since _broadcast is otherwise a plain async function with
no other FastAPI machinery involved.
"""

import asyncio

from app import main as main_module
from app.lobby import Lobby


class FakeWebSocket:
    def __init__(self):
        self.sent = []
        self.on_send = None

    async def send_json(self, message):
        self.sent.append(message)
        if self.on_send:
            self.on_send()


def test_broadcast_survives_a_player_disconnecting_mid_broadcast(monkeypatch):
    lobby = Lobby()
    monkeypatch.setattr(main_module, "lobby", lobby)

    ws_a, ws_b = FakeWebSocket(), FakeWebSocket()
    lobby.add_player(ws_a)
    lobby.add_player(ws_b)
    # Simulates ws_b disconnecting while _broadcast is still mid-loop
    # sending to ws_a -- exactly the interleaving a real concurrent
    # disconnect produces once send_json's await yields control.
    ws_a.on_send = lambda: lobby.remove_player(ws_b)

    asyncio.run(main_module._broadcast({"type": "game_state"}))

    assert ws_a.sent == [{"type": "game_state"}]
    assert ws_b not in lobby.players
