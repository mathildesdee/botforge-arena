from app import interpreter
from app.robot import Robot

DEFAULT_BUILD = {
    "speed": 20, "armor": 15, "weapon_power": 25,
    "accuracy": 20, "fire_rate": 10, "sensor_range": 10,
}


def make_robot(robot_id, x, y, direction, logic, build=None):
    return Robot(robot_id, robot_id, x, y, direction, build or DEFAULT_BUILD, logic)


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
