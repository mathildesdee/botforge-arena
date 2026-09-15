// Best-effort client-side re-implementation of the real interpreter
// (backend/app/interpreter.py), used ONLY to explain a player's OWN
// robot's decisions to them. Deliberately limited to that case: it
// needs the robot's full JSON, which a spectator never receives for
// anyone else's robot (and must not — see docs/ARCHITECTURE.md's
// "information has a cost" / "never expose an enemy's program"
// rules), so there is no way to debug someone else's robot, by
// design, not as an oversight.
//
// This never affects gameplay — it's a parallel, read-only
// computation purely for a debug panel. The real, authoritative
// outcome always comes from the server's own game_state. A few
// server-internal values (weapon cooldown, exact shots fired/hit)
// aren't broadcast at all and so aren't shown here rather than
// guessed at.
//
// Two backend constants are duplicated here because they aren't part
// of the WebSocket contract and there's no other way to get them
// client-side; if backend/app/robot.py changes them, this drifts out
// of sync silently. Documented rather than hidden.
const ASSUMED_MAX_ENERGY = 100; // robot.py DEFAULT_MAX_ENERGY
const BASE_SENSOR_RANGE = 220; // robot.py BASE_SENSOR_RANGE
const SENSOR_RANGE_PER_POINT = 6; // robot.py SENSOR_RANGE_PER_POINT

function resolve(value, context) {
  if (typeof value === 'number' || typeof value === 'boolean') return value;
  let node = context;
  for (const part of value.split('.')) {
    if (node == null || typeof node !== 'object' || !(part in node)) return null;
    node = node[part];
  }
  return node;
}

function evaluateCondition(condition, context) {
  const { op } = condition;
  if (op === 'not') return !evaluateCondition(condition.left, context);
  if (op === 'and') {
    return evaluateCondition(condition.left, context) && evaluateCondition(condition.right, context);
  }
  if (op === 'or') {
    return evaluateCondition(condition.left, context) || evaluateCondition(condition.right, context);
  }

  const left = resolve(condition.left, context);
  const right = resolve(condition.right, context);
  if (op === 'lt') return left < right;
  if (op === 'gt') return left > right;
  if (op === 'eq') return left === right;
  if (op === 'neq') return left !== right;
  return false;
}

// Builds a full trace over every rule, in priority order — not just
// the winning one — so a UI can show the whole cascade (PDF section
// 27, "logic visualization"): which rules were checked and found
// false, which one matched (or fired its `else`) and actually drove
// this tick's action, and which later rules were never reached
// because an earlier one already won. This mirrors
// backend/app/interpreter.py's actual cascade exactly; it just also
// records what happened at each step instead of stopping at the
// first answer.
function decide(logic, context) {
  const sorted = [...logic].sort((a, b) => a.priority - b.priority);
  const trace = [];
  let winner = null;

  for (const rule of sorted) {
    if (winner) {
      trace.push({ priority: rule.priority, description: describeRule(rule), status: 'unreached' });
      continue;
    }
    if (evaluateCondition(rule.if, context)) {
      trace.push({ priority: rule.priority, description: describeRule(rule), status: 'matched' });
      winner = { action: rule.then, rule };
    } else if (rule.else) {
      trace.push({ priority: rule.priority, description: describeRule(rule), status: 'else' });
      winner = { action: rule.else, rule };
    } else {
      trace.push({ priority: rule.priority, description: describeRule(rule), status: 'false' });
    }
  }

  return { action: winner?.action ?? null, rule: winner?.rule ?? null, trace };
}

function describeCondition(condition) {
  if (condition.op === 'not') return `NOT (${describeCondition(condition.left)})`;
  if (condition.op === 'and' || condition.op === 'or') {
    return `(${describeCondition(condition.left)}) ${condition.op.toUpperCase()} (${describeCondition(condition.right)})`;
  }
  const symbols = { lt: '<', gt: '>', eq: '=', neq: '≠' };
  return `${condition.left} ${symbols[condition.op] || condition.op} ${condition.right}`;
}

function describeActionRef(actionRef) {
  return Array.isArray(actionRef) ? actionRef.map(describeActionRef).join(' + ') : actionRef;
}

function describeRule(rule) {
  const elsePart = rule.else ? ` ELSE ${describeActionRef(rule.else)}` : '';
  return `IF ${describeCondition(rule.if)} THEN ${describeActionRef(rule.then)}${elsePart}`;
}

// Mirrors backend/app/interpreter.py's _expand_actions exactly: a
// rule's then/else is a literal action, a name referencing the
// robot's own "behaviours" list (PDF stage 9), or a list mixing
// either (stage 8) — always flattened into literal actions in order.
function expandActions(actionRef, behaviours) {
  if (Array.isArray(actionRef)) {
    return actionRef.flatMap((item) => expandActions(item, behaviours));
  }
  if (actionRef in behaviours) {
    return [...behaviours[actionRef]];
  }
  return [actionRef];
}

export function createRobotDebugger(robotDefinition) {
  const sensorRange = BASE_SENSOR_RANGE + robotDefinition.build.sensor_range * SENSOR_RANGE_PER_POINT;
  const memory = { lastEnemyPosition: null, secondsSinceEnemySeen: 0, previousHealthPct: null, targetId: null };

  function dist(a, b) {
    return Math.hypot(a.x - b.x, a.y - b.y);
  }

  function visibleEnemies(self, others) {
    return others.filter((r) => r.alive && dist(r, self) <= sensorRange);
  }

  // Mirrors backend/app/interpreter.py's _current_enemy exactly: an
  // already-locked target (memory.targetId) sticks as long as it's
  // still visible, so turn_toward_enemy etc. keep tracking the same
  // robot tick to tick — only falling back to "nearest visible" once
  // there's no target, or the locked one is no longer in range.
  function currentEnemy(self, visible) {
    if (memory.targetId) {
      const targeted = visible.find((r) => r.id === memory.targetId);
      if (targeted) return targeted;
    }
    if (visible.length === 0) return null;
    return visible.reduce((nearest, r) => (dist(r, self) < dist(nearest, self) ? r : nearest));
  }

  // Evaluated once per game_state frame for the debugged robot.
  // `self` and `others` are entries straight from game_state.robots.
  function evaluate(self, others, dt) {
    const visible = visibleEnemies(self, others);
    const enemy = currentEnemy(self, visible);

    if (enemy) {
      memory.lastEnemyPosition = { x: enemy.x, y: enemy.y };
      memory.secondsSinceEnemySeen = 0;
    } else if (memory.lastEnemyPosition) {
      memory.secondsSinceEnemySeen += dt;
    }

    const healthPct = (self.health / self.max_health) * 100;

    const context = {
      self: {
        health_pct: healthPct,
        energy_pct: (self.energy / ASSUMED_MAX_ENERGY) * 100,
        previous_health_pct: memory.previousHealthPct ?? healthPct,
        x: self.x,
        y: self.y,
        direction: self.direction,
        seconds_since_enemy_seen: memory.secondsSinceEnemySeen,
        shots_fired: null,
        shots_hit: null,
      },
      enemy: enemy
        ? {
            distance: Math.hypot(enemy.x - self.x, enemy.y - self.y),
            health_pct: (enemy.health / enemy.max_health) * 100,
            direction: enemy.direction,
            visible: true,
          }
        : { distance: Infinity, health_pct: 0, direction: 0, visible: false },
      vars: robotDefinition.variables || {},
    };

    const { action, rule, trace } = decide(robotDefinition.logic || [], context);
    const actions = action !== null ? expandActions(action, robotDefinition.behaviours || {}) : [];

    // Mirrors the *fixed* backend/app/interpreter.py: both selection
    // actions recompute fresh from `visible`, not the sticky `enemy` —
    // select_nearest_enemy must mean "nearest right now", even when a
    // farther target is already locked in memory.targetId.
    if (actions.includes('select_nearest_enemy')) {
      memory.targetId = visible.length > 0
        ? visible.reduce((nearest, r) => (dist(r, self) < dist(nearest, self) ? r : nearest)).id
        : null;
    } else if (actions.includes('select_weakest_enemy')) {
      memory.targetId = visible.length > 0
        ? visible.reduce((weakest, r) => (r.health < weakest.health ? r : weakest)).id
        : null;
    }

    memory.previousHealthPct = healthPct;

    return {
      enemyName: enemy ? enemy.name : null,
      enemyDistance: enemy ? Math.round(context.enemy.distance) : null,
      actions,
      rulePriority: rule ? rule.priority : null,
      ruleDescription: rule ? describeRule(rule) : 'no rule matched',
      trace,
    };
  }

  return { evaluate };
}
