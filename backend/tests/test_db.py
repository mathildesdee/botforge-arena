from app.match import RoundResult
from app.robot import Robot

from app import db

SAMPLE = {
    "name": "Hunter", "version": 1, "creator": "alice",
    "build": {"speed": 20, "armor": 15, "weapon_power": 25, "accuracy": 20, "fire_rate": 10, "sensor_range": 10},
    "logic": [],
}
OPPONENT = {
    "name": "Tank", "version": 1, "creator": "bob",
    "build": {"speed": 5, "armor": 40, "weapon_power": 20, "accuracy": 15, "fire_rate": 10, "sensor_range": 10},
    "logic": [],
}
NEUTRAL_BUILD = {"speed": 0, "armor": 0, "weapon_power": 0, "accuracy": 0, "fire_rate": 0, "sensor_range": 0}


def test_save_robot_version_increments_per_robot(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()

    robot_id, version, version_id = db.save_robot_version("alice", SAMPLE)
    assert version == 1

    robot_id2, version2, version_id2 = db.save_robot_version("alice", {**SAMPLE, "version": 2})
    assert robot_id2 == robot_id
    assert version2 == 2
    assert version_id2 != version_id


def test_leaderboard_reflects_rounds_and_match_stats(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()

    _, _, hunter_version_id = db.save_robot_version("alice", SAMPLE)
    _, _, tank_version_id = db.save_robot_version("bob", OPPONENT)
    lookup = {"arena_robot_1": hunter_version_id, "arena_robot_2": tank_version_id}

    match_id = db.create_match(list(lookup.values()))

    round1 = RoundResult(round_number=1, winner_id="arena_robot_1", survivors=["arena_robot_1"],
                          points_awarded={"arena_robot_1": 3}, duration=12.0)
    round2 = RoundResult(round_number=2, winner_id="arena_robot_2", survivors=["arena_robot_2"],
                          points_awarded={"arena_robot_2": 3}, duration=8.0)
    db.record_round_result(match_id, round1, lookup)
    db.record_round_result(match_id, round2, lookup)

    hunter = Robot("arena_robot_1", "Hunter", 0, 0, 0, NEUTRAL_BUILD, [])
    hunter.damage_caused, hunter.damage_received = 40.0, 25.0
    hunter.shots_fired, hunter.hits_landed, hunter.kills = 10, 4, 1

    tank = Robot("arena_robot_2", "Tank", 0, 0, 0, NEUTRAL_BUILD, [])
    tank.damage_caused, tank.damage_received = 25.0, 40.0
    tank.shots_fired, tank.hits_landed, tank.kills = 8, 3, 1

    db.record_match_stats(match_id, lookup, [hunter, tank])
    db.finish_match(match_id)

    leaderboard = db.get_leaderboard()
    assert len(leaderboard) == 2
    by_name = {row["robot_name"]: row for row in leaderboard}

    hunter_row = by_name["Hunter"]
    assert hunter_row["creator"] == "alice"
    assert hunter_row["matches"] == 1
    assert hunter_row["rounds_won"] == 1
    assert hunter_row["rounds_lost"] == 1
    assert hunter_row["win_pct"] == 0.5
    assert hunter_row["damage_caused"] == 40.0
    assert hunter_row["damage_received"] == 25.0
    assert hunter_row["accuracy"] == 0.4
    assert hunter_row["kills"] == 1
    assert "rank" in hunter_row


def test_leaderboard_row_defaults_when_robot_has_no_matches_yet(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test2.db")
    db.init_db()
    db.save_robot_version("bob", SAMPLE)

    leaderboard = db.get_leaderboard()
    assert leaderboard[0]["matches"] == 0
    assert leaderboard[0]["rounds_won"] == 0
    assert leaderboard[0]["win_pct"] == 0.0
    assert leaderboard[0]["accuracy"] == 0.0
