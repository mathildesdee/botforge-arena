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

MAX_ACTIONS_PER_RULE = 5
MAX_BEHAVIOUR_LENGTH = 5


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

    behaviour_names = set()
    if "behaviours" in data:
        behaviour_errors, behaviour_names = _validate_behaviours(data["behaviours"])
        errors.extend(behaviour_errors)

    if "logic" in data:
        errors.extend(_validate_logic(data["logic"], behaviour_names))

    if "variables" in data:
        errors.extend(_validate_variables(data["variables"]))

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


def _validate_variables(variables):
    """Optional player-defined named numbers (PDF section 21), e.g.
    {"aggression": 70, "preferred_distance": 300} — referenced in
    conditions as "vars.aggression"."""
    if not isinstance(variables, dict):
        return [_err("variables", "Field 'variables' must be an object mapping names to numbers.")]

    errors = []
    for name, value in variables.items():
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            errors.append(_err(f"variables.{name}", f"Variable '{name}' must be a number."))
    return errors


def _validate_behaviours(behaviours):
    """Optional named, reusable action sequences (PDF section 25, stage
    9), e.g. {"retreat": ["turn_toward_enemy", "move_backward"]} — a
    rule's "then"/"else" may reference "retreat" instead of repeating
    the same action list. Returns (errors, valid_behaviour_names)."""
    if not isinstance(behaviours, dict):
        return [_err("behaviours", "Field 'behaviours' must be an object mapping names to action lists.")], set()

    errors = []
    names = set()
    for name, actions in behaviours.items():
        if not isinstance(actions, list) or not actions:
            errors.append(_err(f"behaviours.{name}", f"Behaviour '{name}' must be a non-empty list of actions."))
            continue
        if len(actions) > MAX_BEHAVIOUR_LENGTH:
            errors.append(_err(
                f"behaviours.{name}",
                f"Behaviour '{name}' has {len(actions)} actions; the maximum is {MAX_BEHAVIOUR_LENGTH}.",
            ))
            continue
        bad = [a for a in actions if a not in ALLOWED_ACTIONS]
        if bad:
            errors.append(_err(f"behaviours.{name}", f"Behaviour '{name}' has unrecognized action(s): {', '.join(map(str, bad))}."))
            continue
        names.add(name)

    return errors, names


def _validate_action_ref(value, field_path, label, behaviour_names):
    """An action reference is either a single action/behaviour name, or
    a list of 1-5 of them run together in one tick (PDF stage 8)."""
    if isinstance(value, list):
        if not value:
            return [_err(field_path, f"{label} action list cannot be empty.")]
        if len(value) > MAX_ACTIONS_PER_RULE:
            return [_err(field_path, f"{label} has {len(value)} actions; the maximum is {MAX_ACTIONS_PER_RULE}.")]
        errors = []
        for item in value:
            if item not in ALLOWED_ACTIONS and item not in behaviour_names:
                errors.append(_err(field_path, f"{label} action '{item}' is not a recognized action or behaviour."))
        return errors

    if value not in ALLOWED_ACTIONS and value not in behaviour_names:
        return [_err(field_path, f"{label} action '{value}' is not a recognized action or behaviour.")]
    return []


def _validate_logic(logic, behaviour_names=frozenset()):
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
        else:
            errors.extend(_validate_action_ref(
                rule["then"], f"{field_prefix}.then", f"Rule #{index + 1}", behaviour_names,
            ))

        if "else" in rule:
            errors.extend(_validate_action_ref(
                rule["else"], f"{field_prefix}.else", f"Rule #{index + 1}", behaviour_names,
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
