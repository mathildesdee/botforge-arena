from app import interpreter
from app.robot import Robot

DEFAULT_BUILD = {
    "speed": 20, "armor": 15, "weapon_power": 25,
    "accuracy": 20, "fire_rate": 10, "sensor_range": 10,
}


def make_robot(robot_id, x, y, direction, logic, build=None, behaviours=None):
    return Robot(robot_id, robot_id, x, y, direction, build or DEFAULT_BUILD, logic, behaviours=behaviours)


def test_first_matching_rule_wins_by_priority():
    robot = make_robot("r1", 0, 0, 0, logic=[
        {"priority": 2, "if": {"op": "eq", "left": 1, "right": 1}, "then": "wait"},
        {"priority": 1, "if": {"op": "eq", "left": 1, "right": 1}, "then": "turn_left"},
    ])
    action = interpreter.decide_and_act(robot, [], dt=0.1, arena_width=800, arena_height=600,
                                         fire_callback=lambda r: None)
    assert action == "turn_left"


def test_no_matching_rule_returns_none():
    robot = make_robot("r1", 0, 0, 0, logic=[
        {"priority": 1, "if": {"op": "eq", "left": 1, "right": 2}, "then": "wait"},
    ])
    action = interpreter.decide_and_act(robot, [], dt=0.1, arena_width=800, arena_height=600,
                                         fire_callback=lambda r: None)
    assert action is None


def test_shoot_action_invokes_fire_callback():
    robot = make_robot("r1", 0, 0, 0, logic=[
        {"priority": 1, "if": {"op": "eq", "left": 1, "right": 1}, "then": "shoot"},
    ])
    fired = []
    interpreter.decide_and_act(robot, [], dt=0.1, arena_width=800, arena_height=600,
                                fire_callback=lambda r: fired.append(r.id))
    assert fired == ["r1"]


def test_and_or_not_compose_correctly():
    condition = {
        "op": "and",
        "left": {"op": "not", "left": {"op": "eq", "left": 1, "right": 2}},
        "right": {"op": "or",
                  "left": {"op": "eq", "left": 1, "right": 2},
                  "right": {"op": "eq", "left": 3, "right": 3}},
    }
    robot = make_robot("r1", 0, 0, 0, logic=[{"priority": 1, "if": condition, "then": "wait"}])
    action = interpreter.decide_and_act(robot, [], dt=0.1, arena_width=800, arena_height=600,
                                         fire_callback=lambda r: None)
    assert action == "wait"


def test_operation_limit_skips_turn():
    huge_condition = {"op": "eq", "left": 1, "right": 2}
    for _ in range(60):
        huge_condition = {"op": "and", "left": huge_condition, "right": {"op": "eq", "left": 1, "right": 2}}
    robot = make_robot("r1", 0, 0, 0, logic=[{"priority": 1, "if": huge_condition, "then": "wait"}])

    action = interpreter.decide_and_act(robot, [], dt=0.1, arena_width=800, arena_height=600,
                                         fire_callback=lambda r: None, max_operations=50)
    assert action is None


def test_select_nearest_enemy_targets_closest_visible_robot():
    robot = make_robot("r1", 0, 0, 0, logic=[
        {"priority": 1, "if": {"op": "eq", "left": 1, "right": 1}, "then": "select_nearest_enemy"},
    ])
    near = make_robot("near", 10, 0, 0, logic=[])
    far = make_robot("far", 500, 0, 0, logic=[])
    interpreter.decide_and_act(robot, [far, near], dt=0.1, arena_width=800, arena_height=600,
                                fire_callback=lambda r: None)
    assert robot.target_id == "near"


def test_select_weakest_enemy_targets_lowest_health():
    robot = make_robot("r1", 0, 0, 0, logic=[
        {"priority": 1, "if": {"op": "eq", "left": 1, "right": 1}, "then": "select_weakest_enemy"},
    ])
    healthy = make_robot("healthy", 10, 0, 0, logic=[])
    hurt = make_robot("hurt", 500, 0, 0, logic=[])
    hurt.health = 10
    interpreter.decide_and_act(robot, [healthy, hurt], dt=0.1, arena_width=800, arena_height=600,
                                fire_callback=lambda r: None)
    assert robot.target_id == "hurt"


def test_move_toward_enemy_reduces_distance():
    robot = make_robot("r1", 0, 300, 0, logic=[
        {"priority": 1, "if": {"op": "eq", "left": 1, "right": 1}, "then": "move_toward_enemy"},
    ])
    enemy = make_robot("e1", 400, 300, 0, logic=[])
    start_distance = abs(enemy.x - robot.x)
    interpreter.decide_and_act(robot, [enemy], dt=0.5, arena_width=800, arena_height=600,
                                fire_callback=lambda r: None)
    end_distance = abs(enemy.x - robot.x)
    assert end_distance < start_distance


def test_no_enemy_visible_makes_enemy_conditions_false():
    robot = make_robot("r1", 0, 0, 0, logic=[
        {"priority": 1, "if": {"op": "lt", "left": "enemy.distance", "right": 100}, "then": "shoot"},
        {"priority": 2, "if": {"op": "eq", "left": 1, "right": 1}, "then": "wait"},
    ])
    action = interpreter.decide_and_act(robot, [], dt=0.1, arena_width=800, arena_height=600,
                                         fire_callback=lambda r: None)
    assert action == "wait"


def test_move_forward_is_blocked_when_energy_depleted():
    robot = make_robot("r1", 100, 100, 0, logic=[
        {"priority": 1, "if": {"op": "eq", "left": 1, "right": 1}, "then": "move_forward"},
    ])
    robot.energy = 0.0
    interpreter.decide_and_act(robot, [], dt=1.0, arena_width=800, arena_height=600,
                                fire_callback=lambda r: None)
    assert robot.x == 100  # no energy, so the move never happens


def test_shoot_always_invokes_fire_callback_regardless_of_energy():
    # The interpreter itself doesn't gate "shoot" on energy — that's the
    # fire callback's job (see test_arena.py), same as the cooldown check.
    robot = make_robot("r1", 0, 0, 0, logic=[
        {"priority": 1, "if": {"op": "eq", "left": 1, "right": 1}, "then": "shoot"},
    ])
    robot.energy = 0.0
    fired = []
    interpreter.decide_and_act(robot, [], dt=0.1, arena_width=800, arena_height=600,
                                fire_callback=lambda r: fired.append(r.id))
    assert fired == ["r1"]


def test_else_fires_when_condition_is_false_and_ends_the_cascade():
    robot = make_robot("r1", 0, 0, 0, logic=[
        {"priority": 1, "if": {"op": "eq", "left": 1, "right": 2}, "then": "shoot", "else": "wait"},
        {"priority": 2, "if": {"op": "eq", "left": 1, "right": 1}, "then": "turn_left"},
    ])
    action = interpreter.decide_and_act(robot, [], dt=0.1, arena_width=800, arena_height=600,
                                         fire_callback=lambda r: None)
    # Rule 1's condition is false, but it has an "else" — that resolves the
    # whole decision; rule 2 (which would otherwise match) is never reached.
    assert action == "wait"


def test_else_is_ignored_when_the_condition_is_true():
    robot = make_robot("r1", 0, 0, 0, logic=[
        {"priority": 1, "if": {"op": "eq", "left": 1, "right": 1}, "then": "shoot", "else": "wait"},
    ])
    fired = []
    action = interpreter.decide_and_act(robot, [], dt=0.1, arena_width=800, arena_height=600,
                                         fire_callback=lambda r: fired.append(r.id))
    assert action == "shoot"
    assert fired == ["r1"]


def test_vars_namespace_is_resolvable_in_conditions():
    robot = make_robot("r1", 0, 0, 0, logic=[
        {"priority": 1, "if": {"op": "gt", "left": "vars.aggression", "right": 50}, "then": "shoot"},
        {"priority": 2, "if": {"op": "eq", "left": 1, "right": 1}, "then": "wait"},
    ])
    robot.variables = {"aggression": 70}
    fired = []
    action = interpreter.decide_and_act(robot, [], dt=0.1, arena_width=800, arena_height=600,
                                         fire_callback=lambda r: fired.append(r.id))
    assert action == "shoot"
    assert fired == ["r1"]


def test_seconds_since_enemy_seen_tracks_visibility():
    robot = make_robot("r1", 0, 0, 0, logic=[])
    enemy = make_robot("e1", 10, 0, 0, logic=[])

    interpreter.decide_and_act(robot, [enemy], dt=0.5, arena_width=800, arena_height=600,
                                fire_callback=lambda r: None)
    assert robot.seconds_since_enemy_seen == 0.0

    interpreter.decide_and_act(robot, [], dt=0.5, arena_width=800, arena_height=600,
                                fire_callback=lambda r: None)
    assert robot.seconds_since_enemy_seen == 0.5


def test_move_toward_enemy_falls_back_to_last_known_position_once_out_of_sight():
    robot = make_robot("r1", 100, 300, 0, logic=[
        {"priority": 1, "if": {"op": "eq", "left": 1, "right": 1}, "then": "move_toward_enemy"},
    ])
    enemy = make_robot("e1", 400, 300, 0, logic=[])

    # Enemy briefly visible — robot remembers where it was.
    interpreter.decide_and_act(robot, [enemy], dt=0.1, arena_width=800, arena_height=600,
                                fire_callback=lambda r: None)
    assert robot.last_enemy_position == (400, 300)

    x_before = robot.x
    # Enemy no longer visible, but the robot should still close in on the
    # remembered position rather than freezing.
    interpreter.decide_and_act(robot, [], dt=0.5, arena_width=800, arena_height=600,
                                fire_callback=lambda r: None)
    assert robot.x > x_before


def test_previous_health_pct_reflects_health_before_the_last_ticks_damage():
    # "then" fires when previous health was strictly higher than current
    # health, i.e. "I was just damaged"; "else" otherwise.
    robot = make_robot("r1", 0, 0, 0, logic=[
        {"priority": 1,
         "if": {"op": "gt", "left": "self.previous_health_pct", "right": "self.health_pct"},
         "then": "wait", "else": "turn_left"},
    ])

    # Nothing has happened yet: previous == current -> "else".
    action1 = interpreter.decide_and_act(robot, [], dt=0.1, arena_width=800, arena_height=600,
                                          fire_callback=lambda r: None)
    assert action1 == "turn_left"

    robot.apply_damage(30)  # simulate this tick's combat resolution landing a hit

    # previous_health_pct (captured before the hit, still 100) is now
    # greater than health_pct (70) -> "then".
    action2 = interpreter.decide_and_act(robot, [], dt=0.1, arena_width=800, arena_height=600,
                                          fire_callback=lambda r: None)
    assert action2 == "wait"


def test_then_as_a_list_performs_every_action_in_one_tick():
    robot = make_robot("r1", 0, 0, 0, logic=[
        {"priority": 1, "if": {"op": "eq", "left": 1, "right": 1}, "then": ["turn_left", "shoot"]},
    ])
    start_direction = robot.direction
    fired = []
    interpreter.decide_and_act(robot, [], dt=0.1, arena_width=800, arena_height=600,
                                fire_callback=lambda r: fired.append(r.id))
    # Both actions in the sequence ran this same tick.
    assert robot.direction != start_direction
    assert fired == ["r1"]


def test_behaviour_name_expands_to_its_action_list():
    robot = make_robot("r1", 0, 0, 0, logic=[
        {"priority": 1, "if": {"op": "eq", "left": 1, "right": 1}, "then": "aggressive_shot"},
    ], behaviours={"aggressive_shot": ["turn_left", "shoot"]})
    start_direction = robot.direction
    fired = []
    interpreter.decide_and_act(robot, [], dt=0.1, arena_width=800, arena_height=600,
                                fire_callback=lambda r: fired.append(r.id))
    assert robot.direction != start_direction
    assert fired == ["r1"]


def test_behaviour_referenced_from_within_a_list_also_expands():
    robot = make_robot("r1", 0, 0, 0, logic=[
        {"priority": 1, "if": {"op": "eq", "left": 1, "right": 1}, "then": ["scan", "aggressive_shot"]},
    ], behaviours={"aggressive_shot": ["turn_left", "shoot"]})
    fired = []
    interpreter.decide_and_act(robot, [], dt=0.1, arena_width=800, arena_height=600,
                                fire_callback=lambda r: fired.append(r.id))
    assert fired == ["r1"]


def test_unknown_behaviour_name_is_ignored_like_an_unrecognized_action():
    robot = make_robot("r1", 0, 0, 0, logic=[
        {"priority": 1, "if": {"op": "eq", "left": 1, "right": 1}, "then": "not_a_real_behaviour"},
    ])
    # Should not raise — an unrecognized name/action is just logged and skipped.
    action = interpreter.decide_and_act(robot, [], dt=0.1, arena_width=800, arena_height=600,
                                         fire_callback=lambda r: None)
    assert action == "not_a_real_behaviour"
