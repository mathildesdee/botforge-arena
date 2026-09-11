# Architecture & Shared Contracts

The Python server is always authoritative: it decides positions, hits, damage, and winners. The browser only visualizes what it's told. These contracts let backend and frontend work built in parallel without waiting on each other — build against the shapes below, not against the other side's implementation.

## 1. Game state (sent over WebSocket every tick)

```json
{
  "type": "game_state",
  "tick": 142,
  "robots": [
    {
      "id": "robot_1",
      "name": "Hunter V3",
      "x": 320.5,
      "y": 180.2,
      "direction": 47.0,
      "health": 82,
      "max_health": 100,
      "energy": 61,
      "alive": true
    }
  ],
  "projectiles": [
    { "id": "proj_9", "x": 400.0, "y": 210.0, "direction": 47.0, "owner_id": "robot_1" }
  ],
  "events": [
    { "type": "hit", "target_id": "robot_2", "damage": 14 },
    { "type": "destroyed", "robot_id": "robot_2" }
  ]
}
```

Other message `type`s follow the same envelope shape: `match_start`, `round_start`, `round_end`, `match_end`, `error`.

## 2. Robot build (hardware points)

Exactly 100 points total, distributed across:

```json
{
  "speed": 20,
  "armor": 15,
  "weapon_power": 25,
  "accuracy": 20,
  "fire_rate": 10,
  "sensor_range": 10
}
```

Server rejects any build where the values sum to more than 100.

## 3. Robot program (uploaded JSON)

```json
{
  "name": "Hunter V3",
  "version": 1,
  "creator": "player_name",
  "build": { "speed": 20, "armor": 15, "weapon_power": 25, "accuracy": 20, "fire_rate": 10, "sensor_range": 10 },
  "logic": [
    {
      "priority": 1,
      "if": { "op": "lt", "left": "self.health_pct", "right": 20 },
      "then": "retreat"
    },
    {
      "priority": 2,
      "if": { "op": "lt", "left": "enemy.distance", "right": 200 },
      "then": "shoot"
    }
  ]
}
```

- `logic` rules run in ascending `priority` order; the first matching rule wins for that tick.
- Allowed comparison ops: `lt`, `gt`, `eq`, `neq`, `and`, `or`, `not`.
- Allowed actions (stage 1): `move_forward`, `move_backward`, `turn_left`, `turn_right`, `turn_toward_enemy`, `move_toward_enemy`, `move_away_from_enemy`, `shoot`, `select_nearest_enemy`, `select_weakest_enemy`, `wait`, `scan`.
- Interpreter must cap execution at a fixed number of operations per robot per tick (start at 50) and skip the robot's turn for that tick if exceeded.

## 4. Sensor visibility

A robot only receives enemy data for robots within its `sensor_range`. Never expose an enemy's exact build stats or program — only what a sensor plausibly reveals (distance, direction, estimated health).

## 5. Non-negotiable rules

- The server decides truth; the browser never computes hits or winners itself.
- Uploaded robots are JSON only — never arbitrary code execution.
- Every robot gets exactly 100 build points, no exceptions.
- Game simulation logic stays separate from rendering/visual-effects code.
