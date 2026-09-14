"""The Robot runtime model: build stats, health/energy, and movement.

Field shapes follow docs/ARCHITECTURE.md sections 1 and 2.
"""

import math

BUILD_STATS = ("speed", "armor", "weapon_power", "accuracy", "fire_rate", "sensor_range")

DEFAULT_MAX_HEALTH = 100.0
DEFAULT_MAX_ENERGY = 100.0

BASE_SPEED = 40.0  # px/s at 0 speed points
SPEED_PER_POINT = 1.2

BASE_FIRE_COOLDOWN = 1.6  # seconds at 0 fire_rate points
FIRE_COOLDOWN_REDUCTION_PER_POINT = 0.012
MIN_FIRE_COOLDOWN = 0.3

BASE_SENSOR_RANGE = 220.0
SENSOR_RANGE_PER_POINT = 6.0

TURN_DEGREES_PER_SECOND = 90.0

ARENA_MARGIN = 20.0

# Energy (PDF section 24): movement/scanning/shooting drain it, it slowly
# regenerates, and running dry blocks further action until it recovers —
# so a robot that scans and shoots nonstop can talk itself into a corner.
ENERGY_REGEN_PER_SECOND = 8.0
MOVE_ENERGY_COST_PER_SECOND = 6.0
TURN_ENERGY_COST_PER_SECOND = 2.0
SCAN_ENERGY_COST = 3.0
SHOOT_ENERGY_COST = 8.0


class Robot:
    def __init__(self, robot_id, name, x, y, direction, build, logic=None):
        self.id = robot_id
        self.name = name
        self.x = x
        self.y = y
        self.direction = direction % 360.0
        self.build = build
        self.logic = logic or []

        self.max_health = DEFAULT_MAX_HEALTH
        self.health = self.max_health
        self.max_energy = DEFAULT_MAX_ENERGY
        self.energy = self.max_energy
        self.alive = True

        self.target_id = None
        self.fire_cooldown_remaining = 0.0

        # Cumulative match-level stats (leaderboard). Not reset by respawn() —
        # they span the whole match, not a single round.
        self.shots_fired = 0
        self.hits_landed = 0
        self.damage_caused = 0.0
        self.damage_received = 0.0
        self.kills = 0

    @property
    def speed(self):
        return BASE_SPEED + self.build["speed"] * SPEED_PER_POINT

    @property
    def sensor_range(self):
        return BASE_SENSOR_RANGE + self.build["sensor_range"] * SENSOR_RANGE_PER_POINT

    @property
    def fire_cooldown(self):
        cooldown = BASE_FIRE_COOLDOWN - self.build["fire_rate"] * FIRE_COOLDOWN_REDUCTION_PER_POINT
        return max(MIN_FIRE_COOLDOWN, cooldown)

    def health_pct(self):
        return (self.health / self.max_health) * 100.0 if self.max_health else 0.0

    def energy_pct(self):
        return (self.energy / self.max_energy) * 100.0 if self.max_energy else 0.0

    def tick_cooldowns(self, dt):
        self.fire_cooldown_remaining = max(0.0, self.fire_cooldown_remaining - dt)

    def regenerate_energy(self, dt):
        self.energy = min(self.max_energy, self.energy + ENERGY_REGEN_PER_SECOND * dt)

    def try_consume_energy(self, amount):
        """Deducts `amount` energy and returns True if there was enough;
        otherwise leaves energy untouched and returns False — the caller
        (the interpreter) treats a False result as the action failing to
        execute this tick."""
        if self.energy < amount:
            return False
        self.energy -= amount
        return True

    def move_forward(self, dt, arena_width, arena_height):
        self._move(self.direction, dt, arena_width, arena_height)

    def move_backward(self, dt, arena_width, arena_height):
        self._move(self.direction + 180.0, dt, arena_width, arena_height)

    def _move(self, heading_degrees, dt, arena_width, arena_height):
        # `heading_degrees` may differ from self.direction (e.g. moving
        # backward faces one way but travels the other) — preserve that
        # offset when a wall bounce rewrites the heading.
        offset = heading_degrees - self.direction

        rad = math.radians(heading_degrees)
        new_x = self.x + math.cos(rad) * self.speed * dt
        new_y = self.y + math.sin(rad) * self.speed * dt

        bounced = False
        if new_x < ARENA_MARGIN or new_x > arena_width - ARENA_MARGIN:
            heading_degrees = (180.0 - heading_degrees) % 360.0
            new_x = min(max(new_x, ARENA_MARGIN), arena_width - ARENA_MARGIN)
            bounced = True
        if new_y < ARENA_MARGIN or new_y > arena_height - ARENA_MARGIN:
            heading_degrees = (-heading_degrees) % 360.0
            new_y = min(max(new_y, ARENA_MARGIN), arena_height - ARENA_MARGIN)
            bounced = True

        if bounced:
            self.direction = (heading_degrees - offset) % 360.0
        self.x = new_x
        self.y = new_y

    def turn_left(self, dt, degrees_per_second=TURN_DEGREES_PER_SECOND):
        self.direction = (self.direction - degrees_per_second * dt) % 360.0

    def turn_right(self, dt, degrees_per_second=TURN_DEGREES_PER_SECOND):
        self.direction = (self.direction + degrees_per_second * dt) % 360.0

    def turn_toward(self, target_x, target_y, dt, degrees_per_second=TURN_DEGREES_PER_SECOND):
        desired = math.degrees(math.atan2(target_y - self.y, target_x - self.x)) % 360.0
        diff = (desired - self.direction + 180.0) % 360.0 - 180.0
        step = max(-degrees_per_second * dt, min(degrees_per_second * dt, diff))
        self.direction = (self.direction + step) % 360.0

    def apply_damage(self, amount):
        if not self.alive:
            return
        self.health = max(0.0, self.health - amount)
        if self.health <= 0:
            self.alive = False

    def respawn(self, x, y, direction=0.0):
        self.x, self.y = x, y
        self.direction = direction % 360.0
        self.health = self.max_health
        self.energy = self.max_energy
        self.alive = True
        self.target_id = None
        self.fire_cooldown_remaining = 0.0

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "x": round(self.x, 1),
            "y": round(self.y, 1),
            "direction": round(self.direction, 1),
            "health": round(self.health, 1),
            "max_health": self.max_health,
            "energy": round(self.energy, 1),
            "alive": self.alive,
        }
