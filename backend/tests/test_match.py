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
