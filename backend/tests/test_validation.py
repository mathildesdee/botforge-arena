from app.validation import validate_robot_json

VALID_ROBOT = {
    "name": "Hunter V3",
    "version": 1,
    "creator": "player_name",
    "build": {
        "speed": 20, "armor": 15, "weapon_power": 25,
        "accuracy": 20, "fire_rate": 10, "sensor_range": 10,
    },
    "logic": [
        {"priority": 1, "if": {"op": "lt", "left": "self.health_pct", "right": 20},
         "then": "move_away_from_enemy"},
        {"priority": 2, "if": {"op": "lt", "left": "enemy.distance", "right": 200},
         "then": "shoot"},
    ],
}


def test_valid_robot_passes():
    is_valid, errors = validate_robot_json(VALID_ROBOT)
    assert is_valid
    assert errors == []


def test_rejects_missing_fields():
    is_valid, errors = validate_robot_json({})
    assert not is_valid
    fields = {e["field"] for e in errors}
    assert "name" in fields
    assert "build" in fields
    assert "logic" in fields


def test_rejects_build_over_100_points():
    robot = {**VALID_ROBOT, "build": {**VALID_ROBOT["build"], "speed": 21}}
    is_valid, errors = validate_robot_json(robot)
    assert not is_valid
    assert any("sum to exactly 100" in e["message"] for e in errors)


def test_rejects_missing_build_stat():
    build = dict(VALID_ROBOT["build"])
    del build["armor"]
    robot = {**VALID_ROBOT, "build": build}
    is_valid, errors = validate_robot_json(robot)
    assert not is_valid
    assert any("armor" in e["message"] for e in errors)


def test_rejects_empty_name():
    robot = {**VALID_ROBOT, "name": "   "}
    is_valid, errors = validate_robot_json(robot)
    assert not is_valid


def test_rejects_unknown_action():
    robot = {**VALID_ROBOT, "logic": [
        {"priority": 1, "if": {"op": "lt", "left": 1, "right": 2}, "then": "self_destruct"},
    ]}
    is_valid, errors = validate_robot_json(robot)
    assert not is_valid
    assert any("not a recognized action" in e["message"] for e in errors)


def test_rejects_unknown_condition_operator():
    robot = {**VALID_ROBOT, "logic": [
        {"priority": 1, "if": {"op": "xor", "left": 1, "right": 2}, "then": "wait"},
    ]}
    is_valid, errors = validate_robot_json(robot)
    assert not is_valid


def test_error_messages_are_specific_not_generic():
    is_valid, errors = validate_robot_json(
        {"name": "", "version": 1, "creator": "x", "build": {}, "logic": []}
    )
    assert not is_valid
    assert all(e["message"] != "invalid" for e in errors)
    assert all(e["field"] for e in errors)


def test_accepts_optional_variables():
    robot = {**VALID_ROBOT, "variables": {"aggression": 70, "preferred_distance": 300}}
    is_valid, errors = validate_robot_json(robot)
    assert is_valid
    assert errors == []


def test_rejects_non_numeric_variable():
    robot = {**VALID_ROBOT, "variables": {"aggression": "high"}}
    is_valid, errors = validate_robot_json(robot)
    assert not is_valid
    assert any("aggression" in e["field"] for e in errors)


def test_accepts_else_action_on_a_rule():
    robot = {**VALID_ROBOT, "logic": [
        {"priority": 1, "if": {"op": "eq", "left": "enemy.visible", "right": True},
         "then": "shoot", "else": "wait"},
    ]}
    is_valid, errors = validate_robot_json(robot)
    assert is_valid
    assert errors == []


def test_rejects_unrecognized_else_action():
    robot = {**VALID_ROBOT, "logic": [
        {"priority": 1, "if": {"op": "eq", "left": 1, "right": 1}, "then": "wait", "else": "self_destruct"},
    ]}
    is_valid, errors = validate_robot_json(robot)
    assert not is_valid
    assert any("not a recognized action" in e["message"] for e in errors)
