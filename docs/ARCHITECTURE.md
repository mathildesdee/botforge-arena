# Architecture & Shared Contracts

The Python server is always authoritative: it decides positions, hits, damage, and winners. The browser only visualizes what it's told. These contracts let backend and frontend work built in parallel without waiting on each other — build against the shapes below, not against the other side's implementation.

The frontend is a separate static site from the backend (different origin/port in dev), so `backend/app/main.py` runs with `CORSMiddleware` enabled — without it, a real browser silently blocks `fetch()` calls to `/api/robots/validate` and `/api/leaderboard` even though the server responds fine (found by testing with an actual `Origin` header and an `OPTIONS` preflight, not just `curl`, which doesn't enforce CORS at all). WebSocket connections (`/ws`) aren't subject to CORS, so this only matters for the two REST endpoints.

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
{ "type": "match_start", "total_rounds": 10 }
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

`scores` is the running total across all rounds so far (win = 3pts, survived draw = 1pt, per the project brief), not just this round's points. `round_end` also carries a `replay_id` (the round's `round_results` row id) — see section 9.

An earlier draft of this doc showed `match_start` carrying a `robots` array; the real backend never sends one (nothing reads it either — `ArenaScene.js`'s `match_start` handler only uses `total_rounds`), so it's removed here to match what's actually implemented.

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

`lobby.html` has a "Start tournament" button sending `start_tournament`. `ArenaScene.js` shows current-pairing progress and, on `tournament_end`, a final standings list — both live in `TournamentHud.js`. It doesn't render anything for `tournament_pairing_end`: each pairing already gets the normal per-match winner banner (section 2), so a second summary there would be redundant. Verified `tournament_start`/`tournament_pairing_start` live against a real 3-player tournament; `tournament_end`'s `ranking` shape (the only field the HUD reads) was confirmed by reading `Tournament.standings()` directly rather than waiting out a live run — a single pairing can take up to 10 minutes real-time (10 rounds × 60s cap each).

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

Server rejects any build that doesn't sum to **exactly** 100 — under-spending is rejected too, not just going over (`backend/app/validation.py`'s `_validate_build`: `total != BUILD_POINT_TOTAL`). This line used to say "more than 100," which `builder.html`'s Save/Download gating matched — both only blocked going *over* budget, so a robot with unspent points would pass the builder's own check and then fail real validation. Found via a live `/api/simulate` call while fixing an unrelated test fixture typo.

## 6. Robot program (uploaded JSON)

```json
{
  "name": "Hunter V3",
  "version": 1,
  "creator": "player_name",
  "build": { "speed": 20, "armor": 15, "weapon_power": 25, "accuracy": 20, "fire_rate": 10, "sensor_range": 10 },
  "variables": { "aggression": 70, "preferred_distance": 200 },
  "behaviours": { "retreat": ["turn_toward_enemy", "move_backward"] },
  "logic": [
    {
      "priority": 1,
      "if": { "op": "lt", "left": "self.health_pct", "right": 20 },
      "then": "retreat"
    },
    {
      "priority": 2,
      "if": { "op": "lt", "left": "enemy.distance", "right": "vars.preferred_distance" },
      "then": ["turn_toward_enemy", "shoot"],
      "else": "move_toward_enemy"
    }
  ]
}
```

- `name`, `creator`, `version`, `build`, and `logic` are all required fields — the real validator rejects a robot missing any of them, `logic` included even though no frontend page can author it yet (that's Milestone 5, not built). `builder.html` covers this by asking for a creator name and shipping every robot with a fixed baseline `logic` (find an enemy, close in, shoot) until a real logic editor exists — see `DEFAULT_LOGIC` in `frontend/src/builder.js`. `upload.html` has no such fallback: it validates whatever file it's given and surfaces the real error if a field is missing, which is correct behavior for a validator, not a bug to fix.
- `variables` is optional: player-defined named numbers, resolvable in any condition via a `vars.` prefix (`"vars.preferred_distance"`), exactly like `self.` and `enemy.` below.
- `behaviours` is optional: named, reusable action lists (1-5 actions each, from the same allowed-actions list below — no nesting). A `then`/`else` may reference a behaviour by name instead of repeating its action list.
- `logic` rules run in ascending `priority` order; the first rule whose condition is `true` wins for that tick and its `then` runs. If a rule's condition is `false` **and it has an `else`**, that action runs instead and the cascade still stops there — a rule with `else` always resolves one way or the other. A rule with no `else` that doesn't match just falls through to the next priority, as before.
- `then`/`else` is one of: a literal action name, a behaviour name, or a list of 1-5 of either — every action in the list runs that same tick, in order (e.g. `["turn_toward_enemy", "shoot"]`).
- Allowed comparison ops: `lt`, `gt`, `eq`, `neq`, `and`, `or`, `not`.
- Allowed actions (stage 1): `move_forward`, `move_backward`, `turn_left`, `turn_right`, `turn_toward_enemy`, `move_toward_enemy`, `move_away_from_enemy`, `shoot`, `select_nearest_enemy`, `select_weakest_enemy`, `wait`, `scan`. `turn_toward_enemy`/`move_toward_enemy`/`move_away_from_enemy` fall back to the last known enemy position (see `self.seconds_since_enemy_seen` below) when no enemy is currently visible, instead of doing nothing.
- Interpreter must cap execution at a fixed number of operations per robot per tick (start at 50) and skip the robot's turn for that tick if exceeded. Movement/turning/scanning/shooting also cost energy (see `self.energy_pct` below) — an action whose cost the robot can't afford simply doesn't happen that tick, same as a weapon still on cooldown.
- Condition context available under `self.`: `health_pct`, `energy_pct`, `previous_health_pct` (health going into the *previous* tick — compare against `health_pct` to detect "I was just hit"), `x`, `y`, `direction`, `seconds_since_enemy_seen`, `shots_fired`, `shots_hit`. Under `enemy.`: `distance`, `health_pct`, `direction`, `visible` (all zeroed/false when no enemy is in sensor range).

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

`GET /api/leaderboard` returns an array of these, sorted by rounds won then win percentage — `leaderboard.js` fetches it live. Verified the shapes match exactly against a running `backend/app/db.py`; `frontend/src/mock/leaderboard.mock.json` is no longer used by the page but is left in place as a schema example.

## 9. Replays (Milestone 9, "Replay mode")

Every round is recorded automatically — no opt-in needed. `round_end` (section 2) carries the round's `replay_id`.

`GET /api/replays` — a lightweight index of recorded rounds, newest first, for a "past matches" list:

```json
[
  { "round_result_id": 42, "match_id": 7, "round_number": 3, "duration_seconds": 24.6, "winner_name": "Hunter V3" }
]
```

`GET /api/replays/{round_result_id}` — the full recording for one round:

```json
{
  "found": true,
  "frames": [
    { "type": "game_state", "tick": 1, "robots": [ "...": "..." ], "projectiles": [], "events": [] }
  ],
  "markers": { "first_shot": 12, "first_hit": 34, "final_kill": 210 },
  "health_markers": {
    "robot_1": { "below_50": 88, "below_20": 190 },
    "robot_2": { "below_50": null, "below_20": null }
  }
}
```

`frames` is the exact `game_state` sequence as it was broadcast live — replay it by feeding frames to the same rendering code `ArenaScene.js` already uses for live play, just without a live WebSocket. `markers` and `health_markers` are tick numbers into `frames`, for a scrubber/timeline UI to jump to ("first contact" = `first_shot`, per the project brief's example timeline). A `null` marker means that moment never happened in this round. `{"found": false}` (no `frames` key) means that id doesn't exist or was never recorded — `/api/simulate` runs (section 10) are never recorded, since they're a fast what-if tool, not a real match.

## 10. Fast simulation mode

`POST /api/simulate` — `{"robot_a": {...}, "robot_b": {...}, "rounds": 200}` (both robot bodies match section 6's shape; `rounds` defaults to 100, capped at 2000). Runs headlessly (no real-time pacing, no WebSocket broadcast, nothing persisted) and returns a win/draw tally:

```json
{ "valid": true, "rounds_played": 200, "wins": { "robot_a": 109, "robot_b": 12 }, "draws": 79 }
```

For comparing two robot versions statistically (PDF section 29) instead of watching each one play out live. A `{"valid": false, "field": "robot_a", "errors": [...]}` response (same error shape as section 7) means one of the two robots failed validation before any simulation ran.

## 11. Sensor visibility

A robot only receives enemy data for robots within its `sensor_range`. Never expose an enemy's exact build stats or program — only what a sensor plausibly reveals (distance, direction, estimated health).

## 12. Robot debugger (client-side, own-robot-only)

Clicking a robot in the Arena shows a debug panel. Since `game_state` never includes what a robot is "thinking" (no target, no active rule, no action — only position/health/energy), and never will for other players' robots (their program is never sent to your browser, matching section 11's information-hiding rule), this only works for the robot *you* uploaded:

- The Lobby persists `player.id` and your validated robot JSON to `localStorage` (`botforge:my-player-id`, `botforge:my-robot`) the moment they're known.
- The Arena reads both, and `frontend/src/robotDebugger.js` re-runs the interpreter's exact algorithm (condition evaluation, priority/else, sequence/behaviour expansion — mirrors `backend/app/interpreter.py`) purely to display the result. It never feeds back into gameplay; the server's own broadcast is still the only thing that actually moves anything.
- Clicking any other robot shows only what's already visible on screen (name, health, energy, position) — no target/rule/action, since this browser was never given that robot's program.
- Two backend constants have no other way to reach the client and are duplicated with a comment flagging the coupling: `DEFAULT_MAX_ENERGY` (100) and the `sensor_range` build-stat-to-pixel formula (`BASE_SENSOR_RANGE + stat * SENSOR_RANGE_PER_POINT`). If `backend/app/robot.py` changes either, the debugger drifts silently until someone notices.
- `shots_fired`/`shots_hit` and weapon-cooldown state aren't broadcast at all, so the debugger shows nothing for them rather than guessing.

## 13. Non-negotiable rules

- The server decides truth; the browser never computes hits or winners itself.
- Uploaded robots are JSON only — never arbitrary code execution.
- Every robot gets exactly 100 build points, no exceptions.
- Game simulation logic stays separate from rendering/visual-effects code.
