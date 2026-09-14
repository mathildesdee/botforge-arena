"""Executes a robot's `logic` program each tick.

GitHub issue #6 ("the most important milestone"). Reads the rules described
in docs/ARCHITECTURE.md section 3: evaluate conditions, run rules in
ascending priority order (first match wins), and perform stage-1 actions.
Enforces a max-operations-per-tick limit so a runaway logic tree can't hang
the game loop.

Pure/standalone by design — takes plain Robot-shaped objects and a fire
callback, so it can be unit-tested against sample JSON without the live
WebSocket loop.
"""

import logging

from .combat import distance
from .robot import MOVE_ENERGY_COST_PER_SECOND, SCAN_ENERGY_COST, TURN_ENERGY_COST_PER_SECOND

logger = logging.getLogger("botforge.interpreter")

DEFAULT_MAX_OPERATIONS_PER_TICK = 50


class LogicLimitExceeded(Exception):
    pass


def decide_and_act(robot, visible_enemies, dt, arena_width, arena_height, fire_callback,
                    max_operations=DEFAULT_MAX_OPERATIONS_PER_TICK):
    """Evaluates `robot.logic` against the current world and performs the
    winning rule's action.

    Returns the action name taken, or None if no rule matched or the
    per-tick operation limit was exceeded.
    """
    enemy = _current_enemy(robot, visible_enemies)
    context = _build_context(robot, enemy)
    action = _decide(robot, context, max_operations)
    if action is not None:
        _perform(action, robot, enemy, visible_enemies, dt, arena_width, arena_height, fire_callback)
    return action


def _current_enemy(robot, visible_enemies):
    if robot.target_id:
        targeted = next((r for r in visible_enemies if r.id == robot.target_id), None)
        if targeted is not None:
            return targeted
    if not visible_enemies:
        return None
    return min(visible_enemies, key=lambda r: distance(robot.x, robot.y, r.x, r.y))


def _build_context(robot, enemy):
    self_ctx = {
        "health_pct": robot.health_pct(),
        "energy_pct": robot.energy_pct(),
        "x": robot.x,
        "y": robot.y,
        "direction": robot.direction,
    }
    if enemy is None:
        enemy_ctx = {"distance": float("inf"), "health_pct": 0.0, "direction": 0.0, "visible": False}
    else:
        enemy_ctx = {
            "distance": distance(robot.x, robot.y, enemy.x, enemy.y),
            "health_pct": enemy.health_pct(),
            "direction": enemy.direction,
            "visible": True,
        }
    return {"self": self_ctx, "enemy": enemy_ctx}


def _decide(robot, context, max_operations):
    ops = [0]
    try:
        for rule in sorted(robot.logic, key=lambda r: r["priority"]):
            if _evaluate(rule["if"], context, ops, max_operations):
                return rule["then"]
        return None
    except LogicLimitExceeded:
        logger.warning(
            "Robot %s: logic execution limit (%d ops) reached; skipping turn.",
            robot.id, max_operations,
        )
        return None


def _evaluate(condition, context, ops, max_operations):
    ops[0] += 1
    if ops[0] > max_operations:
        raise LogicLimitExceeded()

    op = condition["op"]
    if op == "not":
        return not _evaluate(condition["left"], context, ops, max_operations)
    if op == "and":
        return (_evaluate(condition["left"], context, ops, max_operations)
                and _evaluate(condition["right"], context, ops, max_operations))
    if op == "or":
        return (_evaluate(condition["left"], context, ops, max_operations)
                or _evaluate(condition["right"], context, ops, max_operations))

    left = _resolve(condition["left"], context)
    right = _resolve(condition["right"], context)
    if op == "lt":
        return left < right
    if op == "gt":
        return left > right
    if op == "eq":
        return left == right
    if op == "neq":
        return left != right
    raise ValueError(f"Unsupported condition operator: {op!r}")


def _resolve(value, context):
    if isinstance(value, (int, float)):
        return value
    node = context
    for part in value.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def _perform(action, robot, enemy, visible_enemies, dt, arena_width, arena_height, fire_callback):
    # Movement, turning, scanning, and shooting cost energy (PDF section
    # 24) — insufficient energy means the action simply doesn't happen
    # this tick, same as a weapon still on cooldown.
    if action == "move_forward":
        if robot.try_consume_energy(MOVE_ENERGY_COST_PER_SECOND * dt):
            robot.move_forward(dt, arena_width, arena_height)
    elif action == "move_backward":
        if robot.try_consume_energy(MOVE_ENERGY_COST_PER_SECOND * dt):
            robot.move_backward(dt, arena_width, arena_height)
    elif action == "turn_left":
        if robot.try_consume_energy(TURN_ENERGY_COST_PER_SECOND * dt):
            robot.turn_left(dt)
    elif action == "turn_right":
        if robot.try_consume_energy(TURN_ENERGY_COST_PER_SECOND * dt):
            robot.turn_right(dt)
    elif action == "turn_toward_enemy":
        if enemy is not None and robot.try_consume_energy(TURN_ENERGY_COST_PER_SECOND * dt):
            robot.turn_toward(enemy.x, enemy.y, dt)
    elif action == "move_toward_enemy":
        if enemy is not None and robot.try_consume_energy(MOVE_ENERGY_COST_PER_SECOND * dt):
            robot.turn_toward(enemy.x, enemy.y, dt)
            robot.move_forward(dt, arena_width, arena_height)
    elif action == "move_away_from_enemy":
        if enemy is not None and robot.try_consume_energy(MOVE_ENERGY_COST_PER_SECOND * dt):
            robot.turn_toward(enemy.x, enemy.y, dt)
            robot.move_backward(dt, arena_width, arena_height)
    elif action == "shoot":
        fire_callback(robot)
    elif action == "select_nearest_enemy":
        robot.target_id = enemy.id if enemy is not None else None
    elif action == "select_weakest_enemy":
        robot.target_id = min(visible_enemies, key=lambda r: r.health_pct()).id if visible_enemies else None
    elif action == "scan":
        robot.try_consume_energy(SCAN_ENERGY_COST)
    elif action == "wait":
        pass
    else:
        logger.warning("Robot %s: unrecognized action %r ignored.", robot.id, action)
