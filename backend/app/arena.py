"""The authoritative arena world: robots, projectiles, and the tick that
advances them, per docs/ARCHITECTURE.md section 1.

GitHub issue #3 (game loop) runs on top of this; combat is delegated to
combat.py (issue #2) and decision-making to interpreter.py (issue #6).
"""

import random

from . import combat
from . import interpreter

ARENA_WIDTH = 800
ARENA_HEIGHT = 600
SPAWN_MARGIN = 60


class Arena:
    def __init__(self, robots):
        self.width = ARENA_WIDTH
        self.height = ARENA_HEIGHT
        self.robots = robots
        self.projectiles = []
        self.tick_count = 0

    def randomize_spawns(self, rng=None):
        rng = rng or random
        for robot in self.robots:
            robot.respawn(
                x=rng.uniform(SPAWN_MARGIN, self.width - SPAWN_MARGIN),
                y=rng.uniform(SPAWN_MARGIN, self.height - SPAWN_MARGIN),
                direction=rng.uniform(0, 360),
            )
        self.projectiles = []

    def _visible_enemies(self, robot):
        return [
            r for r in self.robots
            if r.id != robot.id and r.alive
            and combat.distance(robot.x, robot.y, r.x, r.y) <= robot.sensor_range
        ]

    def tick(self, dt):
        """Reads state, updates robots/projectiles, checks collisions, and
        returns this tick's combat events (for game_state broadcasting)."""
        self.tick_count += 1

        for robot in self.robots:
            if not robot.alive:
                continue
            robot.tick_cooldowns(dt)
            visible_enemies = self._visible_enemies(robot)

            def fire(shooter):
                if shooter.fire_cooldown_remaining > 0:
                    return
                self.projectiles.append(combat.spawn_projectile(shooter))
                shooter.fire_cooldown_remaining = shooter.fire_cooldown
                shooter.shots_fired += 1

            interpreter.decide_and_act(robot, visible_enemies, dt, self.width, self.height, fire)

        for proj in self.projectiles:
            proj.update(dt, self.width, self.height)

        surviving, hit_events = combat.resolve_collisions(self.projectiles, self.robots)
        self.projectiles = [p for p in surviving if p.alive]

        return hit_events

    def state(self, events=None):
        return {
            "type": "game_state",
            "tick": self.tick_count,
            "robots": [r.to_dict() for r in self.robots],
            "projectiles": [p.to_dict() for p in self.projectiles],
            "events": events or [],
        }
