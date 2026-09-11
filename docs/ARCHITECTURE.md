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

## 2. Match lifecycle messages (same WebSocket connection)

These share the connection with `game_state` but arrive far less often — on round/match boundaries rather than every tick. A HUD listens for these to know the round number and score; it does not derive them from `game_state`.

```json
{ "type": "match_start", "total_rounds": 10, "robots": [{ "id": "robot_1", "name": "Hunter V3" }] }
```

```json
{ "type": "round_start", "round": 3, "total_rounds": 10 }
```

```json
{
  "type": "round_end",
  "round": 3,
  "winner_id": "robot_1",
  "scores": { "robot_1": 9, "robot_2": 3 }
}
```

`scores` is the running total across all rounds so far (win = 3pts, survived draw = 1pt, per the project brief), not just this round's points.

```json
{ "type": "match_end", "winner_id": "robot_1", "final_scores": { "robot_1": 24, "robot_2": 9 } }
```

```json
{ "type": "error", "message": "Logic execution limit reached", "robot_id": "robot_2" }
```

## 3. Robot build (hardware points)

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

## 4. Robot program (uploaded JSON)

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

## 5. Robot validation endpoint

`POST /api/robots/validate` — request body is a robot program JSON matching section 4.

Success response `200`:

```json
{ "valid": true, "robot": { "name": "Hunter V3", "version": 1, "build": { "...": "..." }, "logic": [] } }
```

Failure response `422`:

```json
{
  "valid": false,
  "errors": [
    { "field": "build", "message": "Build points sum to 135; the maximum is 100." },
    { "field": "name", "message": "Robot name is required." }
  ]
}
```

- `field` uses dot-path notation matching the robot JSON structure (e.g. `build.speed`, `logic[2].if`), so the frontend can associate an error with a specific part of the upload.
- This same shape is what Milestone 3's builder page will eventually POST to for server-side save/validation, once that endpoint exists.

## 6. Leaderboard entry (persisted stats)

One row per robot, matching what the SQLite persistence layer stores:

```json
{
  "rank": 1,
  "robot_name": "Hunter V3",
  "creator": "player_name",
  "matches": 12,
  "rounds_won": 34,
  "rounds_lost": 11,
  "win_pct": 0.76,
  "damage_caused": 4820,
  "damage_received": 3010,
  "accuracy": 0.47,
  "kills": 18
}
```

The leaderboard page renders a list of these; where the data comes from (static mock JSON today, a real `/api/leaderboard` endpoint once the persistence issue lands) is an implementation detail behind that same shape.

## 7. Sensor visibility

A robot only receives enemy data for robots within its `sensor_range`. Never expose an enemy's exact build stats or program — only what a sensor plausibly reveals (distance, direction, estimated health).

## 8. Non-negotiable rules

- The server decides truth; the browser never computes hits or winners itself.
- Uploaded robots are JSON only — never arbitrary code execution.
- Every robot gets exactly 100 build points, no exceptions.
- Game simulation logic stays separate from rendering/visual-effects code.
