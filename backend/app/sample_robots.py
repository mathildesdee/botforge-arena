"""Two simple built-in robot programs used to run a playable demo match
without requiring an upload first (see main.py's game_loop). Each build
sums to exactly 100 points, per docs/ARCHITECTURE.md section 2.
"""

SAMPLE_ROBOTS = [
    {
        "name": "Hunter",
        "version": 1,
        "creator": "botforge",
        "build": {
            "speed": 25, "armor": 10, "weapon_power": 25,
            "accuracy": 20, "fire_rate": 10, "sensor_range": 10,
        },
        "logic": [
            {"priority": 1, "if": {"op": "lt", "left": "self.health_pct", "right": 20},
             "then": "move_away_from_enemy"},
            {"priority": 2, "if": {"op": "lt", "left": "enemy.distance", "right": 180},
             "then": "shoot"},
            {"priority": 3, "if": {"op": "eq", "left": "enemy.visible", "right": True},
             "then": "move_toward_enemy"},
            {"priority": 4, "if": {"op": "eq", "left": 1, "right": 1}, "then": "move_forward"},
        ],
    },
    {
        "name": "Turret",
        "version": 1,
        "creator": "botforge",
        "build": {
            "speed": 5, "armor": 30, "weapon_power": 30,
            "accuracy": 25, "fire_rate": 10, "sensor_range": 0,
        },
        "logic": [
            {"priority": 1, "if": {"op": "lt", "left": "enemy.distance", "right": 250},
             "then": "shoot"},
            {"priority": 2, "if": {"op": "eq", "left": "enemy.visible", "right": True},
             "then": "turn_toward_enemy"},
            {"priority": 3, "if": {"op": "eq", "left": 1, "right": 1}, "then": "turn_right"},
        ],
    },
]
