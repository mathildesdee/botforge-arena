import random

from app.tournament import Participant, Tournament

BUILD = {"speed": 20, "armor": 15, "weapon_power": 25, "accuracy": 20, "fire_rate": 10, "sensor_range": 10}

AGGRESSIVE_LOGIC = [
    {"priority": 1, "if": {"op": "lt", "left": "enemy.distance", "right": 250}, "then": "shoot"},
    {"priority": 2, "if": {"op": "eq", "left": "enemy.visible", "right": True}, "then": "move_toward_enemy"},
    {"priority": 3, "if": {"op": "eq", "left": 1, "right": 1}, "then": "move_forward"},
]


def make_participant(pid, robot_version_id=None):
    return Participant(pid, pid, dict(BUILD), AGGRESSIVE_LOGIC, robot_version_id=robot_version_id)


def test_schedules_every_unique_pairing():
    participants = [make_participant(f"p{i}") for i in range(4)]
    tournament = Tournament(participants, rng=random.Random(0))

    pairs = {frozenset((a.id, b.id)) for a, b in tournament.pairings}
    assert len(tournament.pairings) == 6  # 4 choose 2
    assert len(pairs) == 6  # all unique, no duplicates or self-pairs
    assert all(a.id != b.id for a, b in tournament.pairings)


def test_run_to_completion_plays_every_pairing_and_produces_standings():
    participants = [make_participant(f"p{i}") for i in range(3)]
    tournament = Tournament(participants, num_rounds=1, round_time_limit=20.0, rng=random.Random(1))

    standings = tournament.run_to_completion(dt=1 / 20)

    assert tournament.finished
    assert len(tournament.pairing_results) == 3  # 3 choose 2
    assert set(standings["totals"].keys()) == {"p0", "p1", "p2"}
    assert len(standings["pairings"]) == 3


def test_standings_ranking_is_sorted_descending_by_points():
    participants = [make_participant(f"p{i}") for i in range(3)]
    tournament = Tournament(participants, num_rounds=1, round_time_limit=20.0, rng=random.Random(2))

    standings = tournament.run_to_completion(dt=1 / 20)

    points = [entry["points"] for entry in standings["ranking"]]
    assert points == sorted(points, reverse=True)
    assert {entry["participant_id"] for entry in standings["ranking"]} == {"p0", "p1", "p2"}


def test_each_pairing_starts_with_fresh_undamaged_robots():
    participants = [make_participant(f"p{i}") for i in range(3)]
    tournament = Tournament(participants, num_rounds=1, round_time_limit=1.0, rng=random.Random(3))

    tournament.start_next_pairing()  # pairing 1: p0 vs p1
    match = tournament.current_match
    while not match.finished:
        match.start_round()
        while True:
            result = match.tick(1 / 20)
            if result["round_result"] is not None:
                break
    tournament.finish_current_pairing()

    tournament.start_next_pairing()  # pairing 2: p0 vs p2 — p0 must not carry damage over
    fresh_robots = tournament.current_match.arena.robots
    assert all(r.health == r.max_health for r in fresh_robots)


def test_empty_participant_list_is_immediately_finished():
    tournament = Tournament([], rng=random.Random(0))
    assert tournament.finished
    assert tournament.start_next_pairing() is None
    assert tournament.standings()["pairings"] == []


def test_new_robot_carries_the_participants_variables_through():
    # Regression: it's easy to wire a robot_definition's build/logic into
    # a Participant/Robot and forget "variables" — the JSON contract's
    # least-used field. If this silently defaults to {}, any "vars.x"
    # condition resolves to None and crashes the interpreter mid-match.
    participant = Participant("p0", "p0", dict(BUILD), AGGRESSIVE_LOGIC, variables={"aggression": 70})
    robot = participant.new_robot()
    assert robot.variables == {"aggression": 70}


def test_new_robot_carries_the_participants_behaviours_through():
    behaviours = {"retreat": ["turn_toward_enemy", "move_backward"]}
    participant = Participant("p0", "p0", dict(BUILD), AGGRESSIVE_LOGIC, behaviours=behaviours)
    robot = participant.new_robot()
    assert robot.behaviours == behaviours
