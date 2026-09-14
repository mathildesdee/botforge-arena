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

## 3. Multiplayer lobby protocol (same `/ws` endpoint as game_state)

Milestone 6. Unlike the first draft of this section, the lobby is **not** a separate endpoint — every WebSocket connection to `/ws` is a lobby member (and a spectator once a match is running) from the moment it connects, before it even sends `join`. This is the real, implemented, and integration-tested protocol — build against this, not against the mock scripts that predate it.

Client → server:

```json
{ "type": "join", "name": "Alice" }
```

```json
{ "type": "upload_robot", "robot": { "...": "a full robot program, section 6" } }
```

```json
{ "type": "set_ready", "ready": true }
```

```json
{ "type": "start_match" }
```

There is no `leave` message — a player leaves by closing the WebSocket connection; the server detects the disconnect and removes them.

Server → client, broadcast to every connected socket whenever membership, names, robots, or readiness change:

```json
{
  "type": "lobby_state",
  "players": [
    { "id": "player_1", "name": "Alice", "ready": true, "has_robot": true },
    { "id": "player_2", "name": "Bob", "ready": false, "has_robot": false }
  ]
}
```

- There is no server-assigned "this is you" message — a client identifies its own row by matching the `name` it sent in `join`. Two players picking the same name is an unhandled edge case for now.
- `has_robot` is a boolean, not a robot name — other players' robot details aren't exposed in the lobby.
- `set_ready: true` is silently downgraded to `false` server-side if the player has no uploaded robot yet.

Server → client, sent only to the uploader, in direct response to `upload_robot`:

```json
{ "type": "robot_upload_result", "valid": true, "robot": { "...": "..." } }
```

```json
{ "type": "robot_upload_result", "valid": false, "errors": [{ "field": "creator", "message": "Missing required field 'creator'." }] }
```

Same error shape as the validation endpoint (section 7) — `upload_robot` runs the exact same validator.

Server → client, sent only to whoever requested `start_match`, if it's rejected (needs 2-8 ready players, one match at a time):

```json
{ "type": "lobby_error", "message": "Need 2-8 ready players (with an uploaded robot each) to start." }
```

On success, `start_match` triggers the match lifecycle messages (section 2) and `game_state` (section 1), broadcast to every connected socket — players and spectators alike, which is how "spectate together" works: anyone with the page open sees the match, not just the players who readied up.

## 4. Tournament protocol (same `/ws` endpoint, Milestone 10)

`{ "type": "start_tournament" }` — same rejection path as `start_match` (`lobby_error`) if fewer than 2 ready players or an activity is already running, sent only to the requester.

On success, every unique pairing among the ready players is scheduled and run as a full match, back to back, broadcasting:

```json
{ "type": "tournament_start", "participants": [{ "id": "player_1", "name": "Alice" }], "total_pairings": 3 }
```

```json
{ "type": "tournament_pairing_start", "pairing": 1, "total_pairings": 3, "participants": ["player_1", "player_2"] }
```

Between `tournament_pairing_start` and `tournament_pairing_end`, that pairing's match runs exactly like a normal match — the same `match_start`/`round_start`/`game_state`/`round_end`/`match_end` messages from sections 1-2, broadcast to everyone (including participants sitting out the current pairing, who are spectating it).

```json
{ "type": "tournament_pairing_end", "pairing": 1, "result": { "...": "winner/scores for this pairing" } }
```

```json
{ "type": "tournament_end", "...": "final standings across all pairings" }
```

No frontend page consumes these yet — a tournament UI (bracket/standings view) is unbuilt.

## 5. Robot build (hardware points)

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

## 6. Robot program (uploaded JSON)

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

- `name`, `creator`, `version`, `build`, and `logic` are all required fields — the real validator rejects a robot missing any of them, `logic` included even though no frontend page can author it yet (that's Milestone 5, not built). `builder.html` covers this by asking for a creator name and shipping every robot with a fixed baseline `logic` (find an enemy, close in, shoot) until a real logic editor exists — see `DEFAULT_LOGIC` in `frontend/src/builder.js`. `upload.html` has no such fallback: it validates whatever file it's given and surfaces the real error if a field is missing, which is correct behavior for a validator, not a bug to fix.
- `logic` rules run in ascending `priority` order; the first matching rule wins for that tick.
- Allowed comparison ops: `lt`, `gt`, `eq`, `neq`, `and`, `or`, `not`.
- Allowed actions (stage 1): `move_forward`, `move_backward`, `turn_left`, `turn_right`, `turn_toward_enemy`, `move_toward_enemy`, `move_away_from_enemy`, `shoot`, `select_nearest_enemy`, `select_weakest_enemy`, `wait`, `scan`.
- Interpreter must cap execution at a fixed number of operations per robot per tick (start at 50) and skip the robot's turn for that tick if exceeded.

## 7. Robot validation endpoint

`POST /api/robots/validate` — request body is a robot program JSON matching section 6.

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

## 8. Leaderboard entry (persisted stats)

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

## 9. Sensor visibility

A robot only receives enemy data for robots within its `sensor_range`. Never expose an enemy's exact build stats or program — only what a sensor plausibly reveals (distance, direction, estimated health).

## 10. Non-negotiable rules

- The server decides truth; the browser never computes hits or winners itself.
- Uploaded robots are JSON only — never arbitrary code execution.
- Every robot gets exactly 100 build points, no exceptions.
- Game simulation logic stays separate from rendering/visual-effects code.
