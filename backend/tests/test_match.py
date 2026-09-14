import random

from app.match import Match
from app.robot import Robot

BUILD = {"speed": 0, "armor": 0, "weapon_power": 0, "accuracy": 0, "fire_rate": 0, "sensor_range": 0}


def make_robot(robot_id):
    return Robot(robot_id, robot_id, x=0, y=0, direction=0, build=dict(BUILD), logic=[])


def test_round_ends_and_awards_win_points_to_sole_survivor():
    winner = make_robot("winner")
    loser = make_robot("loser")

    match = Match([winner, loser], num_rounds=1, round_time_limit=60.0, rng=random.Random(0))
    match.start_round()
    loser.alive = False  # simulate the loser having been destroyed already this round

    result = match.tick(0.1)

    assert result["round_result"].winner_id == "winner"
    assert match.scores["winner"] == 3
    assert match.scores["loser"] == 0
    assert match.finished


def test_round_time_limit_awards_survival_points_to_all_alive():
    a = make_robot("a")
    b = make_robot("b")

    match = Match([a, b], num_rounds=1, round_time_limit=0.05, rng=random.Random(0))
    match.start_round()
    result = match.tick(0.1)

    assert result["round_result"].winner_id is None
    assert match.scores["a"] == 1
    assert match.scores["b"] == 1


def test_match_finishes_after_num_rounds():
    a = make_robot("a")
    b = make_robot("b")
    match = Match([a, b], num_rounds=2, round_time_limit=0.01, rng=random.Random(0))

    match.start_round()
    match.tick(0.1)
    assert not match.finished

    match.start_round()
    match.tick(0.1)
    assert match.finished

    final = match.final_result()
    assert final["scores"]["a"] == 2
    assert len(final["rounds"]) == 2


def test_run_to_completion_drives_every_round_without_a_manual_loop():
    a = make_robot("a")
    b = make_robot("b")
    match = Match([a, b], num_rounds=5, round_time_limit=0.05, rng=random.Random(0))

    final = match.run_to_completion(dt=0.1)

    assert match.finished
    assert len(match.round_results) == 5
    assert final["rounds"] == [r.to_dict() for r in match.round_results]


def test_round_win_counts_tallies_wins_and_draws():
    a = make_robot("a")
    b = make_robot("b")
    # These inert robots (0 build points, no logic) never fight, so every
    # round ends in a survival draw once the time limit is hit.
    match = Match([a, b], num_rounds=10, round_time_limit=0.05, rng=random.Random(0))

    match.run_to_completion(dt=0.1)
    counts = match.round_win_counts()

    assert counts == {"a": 0, "b": 0, "draws": 10}


def test_round_win_counts_credits_a_decisive_winner():
    aggressive_build = {"speed": 20, "armor": 0, "weapon_power": 60, "accuracy": 100, "fire_rate": 20, "sensor_range": 0}
    aggressive_logic = [
        # Shoot only once close (by then, move_toward_enemy will already have
        # turned the robot to face its target over the preceding ticks —
        # "shoot" itself never aims).
        {"priority": 1, "if": {"op": "lt", "left": "enemy.distance", "right": 180}, "then": "shoot"},
        {"priority": 2, "if": {"op": "eq", "left": "enemy.visible", "right": True}, "then": "move_toward_enemy"},
        {"priority": 3, "if": {"op": "eq", "left": 1, "right": 1}, "then": "move_forward"},
    ]
    hunter = Robot("hunter", "hunter", x=0, y=0, direction=0, build=aggressive_build, logic=aggressive_logic)
    victim = Robot("victim", "victim", x=0, y=0, direction=0, build=dict(BUILD), logic=[])

    match = Match([hunter, victim], num_rounds=3, round_time_limit=20.0, rng=random.Random(0))
    match.run_to_completion(dt=1 / 20)
    counts = match.round_win_counts()

    assert counts["hunter"] + counts["victim"] + counts["draws"] == 3
    assert counts["hunter"] >= counts["victim"]  # a fully aggressive bot vs. an inert one should never lose
