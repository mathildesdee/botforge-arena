from app.lobby import Lobby


def test_join_and_leave_updates_player_list():
    lobby = Lobby()
    p1 = lobby.add_player("conn-1")
    lobby.set_name(p1, "Alice")
    assert lobby.state_dict()["players"] == [
        {"id": p1.id, "name": "Alice", "ready": False, "has_robot": False}
    ]

    lobby.remove_player("conn-1")
    assert lobby.state_dict()["players"] == []


def test_cannot_ready_without_a_robot():
    lobby = Lobby()
    p1 = lobby.add_player("conn-1")
    lobby.set_ready(p1, True)
    assert p1.ready is False


def test_uploading_a_robot_allows_ready_and_reuploading_resets_it():
    lobby = Lobby()
    p1 = lobby.add_player("conn-1")
    lobby.set_robot(p1, {"name": "Hunter"}, robot_version_id=42)
    lobby.set_ready(p1, True)
    assert p1.ready is True

    lobby.set_robot(p1, {"name": "Hunter V2"}, robot_version_id=43)
    assert p1.ready is False


def test_can_start_match_requires_between_two_and_eight_ready_players():
    lobby = Lobby()
    players = [lobby.add_player(f"conn-{i}") for i in range(9)]
    for p in players:
        lobby.set_robot(p, {"name": "Bot"}, robot_version_id=1)

    assert not lobby.can_start_match()

    lobby.set_ready(players[0], True)
    assert not lobby.can_start_match()

    for p in players[:2]:
        lobby.set_ready(p, True)
    assert lobby.can_start_match()

    for p in players:
        lobby.set_ready(p, True)
    assert not lobby.can_start_match()  # 9 ready is over the 8-robot cap


def test_reset_ready_states_clears_everyone():
    lobby = Lobby()
    players = [lobby.add_player(f"conn-{i}") for i in range(2)]
    for p in players:
        lobby.set_robot(p, {"name": "Bot"}, robot_version_id=1)
        lobby.set_ready(p, True)

    lobby.reset_ready_states()
    assert all(not p.ready for p in players)


def test_name_is_trimmed_and_length_limited():
    lobby = Lobby()
    p1 = lobby.add_player("conn-1")
    lobby.set_name(p1, "   " + "x" * 100)
    assert len(p1.name) == 24


def test_default_display_name_falls_back_to_player_id():
    lobby = Lobby()
    p1 = lobby.add_player("conn-1")
    assert p1.display_name() == p1.id
