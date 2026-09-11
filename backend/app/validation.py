"""Validates uploaded robot JSON against docs/ARCHITECTURE.md section 3.

Pure validation logic (GitHub issue #5) — no dependency on the interpreter
or game loop. Errors are returned as {"field", "message"} objects matching
the /api/robots/validate response contract the frontend already builds
against (see frontend/src/upload.js).
"""

REQUIRED_TOP_LEVEL_FIELDS = ("name", "version", "creator", "build", "logic")
REQUIRED_BUILD_STATS = ("speed", "armor", "weapon_power", "accuracy", "fire_rate", "sensor_range")
BUILD_POINT_TOTAL = 100

ALLOWED_CONDITION_OPS = {"lt", "gt", "eq", "neq", "and", "or", "not"}
ALLOWED_ACTIONS = {
    "move_forward", "move_backward", "turn_left", "turn_right",
    "turn_toward_enemy", "move_toward_enemy", "move_away_from_enemy",
    "shoot", "select_nearest_enemy", "select_weakest_enemy", "wait", "scan",
}

NAME_MIN_LENGTH = 1
NAME_MAX_LENGTH = 40


def _err(field, message):
    return {"field": field, "message": message}


def validate_robot_json(data):
    """Returns (is_valid, errors). Never raises on malformed input.

    Each error is a {"field", "message"} dict."""
    errors = []

    if not isinstance(data, dict):
        return False, [_err(None, "Robot definition must be a JSON object.")]

    for field in REQUIRED_TOP_LEVEL_FIELDS:
        if field not in data:
            errors.append(_err(field, f"Missing required field '{field}'."))

    if "name" in data:
        errors.extend(_validate_name(data["name"]))

    if "version" in data and not isinstance(data["version"], int):
        errors.append(_err("version", "Field 'version' must be an integer."))

    if "creator" in data and not (isinstance(data["creator"], str) and data["creator"].strip()):
        errors.append(_err("creator", "Field 'creator' must be a non-empty string."))

    if "build" in data:
        errors.extend(_validate_build(data["build"]))

    if "logic" in data:
        errors.extend(_validate_logic(data["logic"]))

    return (len(errors) == 0), errors


def _validate_name(name):
    if not isinstance(name, str):
        return [_err("name", "Field 'name' must be a string.")]
    stripped = name.strip()
    if len(stripped) < NAME_MIN_LENGTH:
        return [_err("name", "Field 'name' cannot be empty.")]
    if len(stripped) > NAME_MAX_LENGTH:
        return [_err("name", f"Field 'name' must be at most {NAME_MAX_LENGTH} characters.")]
    return []


def _validate_build(build):
    if not isinstance(build, dict):
        return [_err("build", "Field 'build' must be an object mapping stat names to point values.")]

    errors = []
    missing = [s for s in REQUIRED_BUILD_STATS if s not in build]
    if missing:
        errors.append(_err("build", f"Build is missing stat(s): {', '.join(missing)}."))

    unknown = [s for s in build if s not in REQUIRED_BUILD_STATS]
    if unknown:
        errors.append(_err("build", f"Build has unknown stat(s): {', '.join(unknown)}."))

    total = 0
    for stat in REQUIRED_BUILD_STATS:
        if stat not in build:
            continue
        value = build[stat]
        if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
            errors.append(_err(f"build.{stat}", f"Build stat '{stat}' must be a non-negative number."))
            continue
        total += value

    if not missing and not unknown and total != BUILD_POINT_TOTAL:
        errors.append(_err("build", f"Build points must sum to exactly {BUILD_POINT_TOTAL}; got {total}."))

    return errors


def _validate_logic(logic):
    if not isinstance(logic, list):
        return [_err("logic", "Field 'logic' must be a list of rules.")]

    errors = []
    if not logic:
        errors.append(_err("logic", "Field 'logic' must contain at least one rule."))

    for index, rule in enumerate(logic):
        field_prefix = f"logic[{index}]"
        if not isinstance(rule, dict):
            errors.append(_err(field_prefix, f"Rule #{index + 1} must be an object."))
            continue

        if "priority" not in rule:
            errors.append(_err(f"{field_prefix}.priority", f"Rule #{index + 1} is missing 'priority'."))
        elif not isinstance(rule["priority"], int) or isinstance(rule["priority"], bool):
            errors.append(_err(f"{field_prefix}.priority", f"Rule #{index + 1} field 'priority' must be an integer."))

        if "if" not in rule:
            errors.append(_err(f"{field_prefix}.if", f"Rule #{index + 1} is missing an 'if' condition."))
        else:
            errors.extend(_validate_condition(rule["if"], f"{field_prefix}.if", index))

        if "then" not in rule:
            errors.append(_err(f"{field_prefix}.then", f"Rule #{index + 1} is missing a 'then' action."))
        elif rule["then"] not in ALLOWED_ACTIONS:
            errors.append(_err(
                f"{field_prefix}.then",
                f"Rule #{index + 1} action '{rule.get('then')}' is not a recognized action.",
            ))

    return errors


def _validate_condition(condition, field_path, rule_index):
    label = f"Rule #{rule_index + 1} condition ({field_path})"

    if not isinstance(condition, dict):
        return [_err(field_path, f"{label} must be an object.")]

    op = condition.get("op")
    if op not in ALLOWED_CONDITION_OPS:
        return [_err(f"{field_path}.op", f"{label} has unrecognized operator '{op}'.")]

    errors = []

    if op == "not":
        if "left" not in condition:
            errors.append(_err(f"{field_path}.left", f"{label} using 'not' is missing 'left'."))
        else:
            errors.extend(_validate_condition(condition["left"], f"{field_path}.left", rule_index))
        return errors

    if op in ("and", "or"):
        for side in ("left", "right"):
            if side not in condition:
                errors.append(_err(f"{field_path}.{side}", f"{label} using '{op}' is missing '{side}'."))
            else:
                errors.extend(_validate_condition(condition[side], f"{field_path}.{side}", rule_index))
        return errors

    # lt, gt, eq, neq: left/right are value refs (dotted-path string) or literals.
    for side in ("left", "right"):
        if side not in condition:
            errors.append(_err(f"{field_path}.{side}", f"{label} using '{op}' is missing '{side}'."))
        elif not isinstance(condition[side], (str, int, float)):
            errors.append(_err(f"{field_path}.{side}", f"{label} field '{side}' must be a string reference or number."))

    return errors
