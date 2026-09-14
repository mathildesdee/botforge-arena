"""Combat system: projectiles, collisions, damage, and destruction.

GitHub issue #2. Built against the Robot shape in robot.py and the event
shapes described in docs/ARCHITECTURE.md section 1.
"""

import itertools
import math
import random

PROJECTILE_SPEED = 320.0  # px/s
PROJECTILE_RADIUS = 4.0
ROBOT_RADIUS = 16.0

BASE_DAMAGE = 6.0
DAMAGE_PER_WEAPON_POINT = 0.14

MAX_ARMOR_REDUCTION = 0.5
ARMOR_REDUCTION_PER_POINT = MAX_ARMOR_REDUCTION / 100.0

ACCURACY_MAX_SPREAD_DEGREES = 18.0  # spread at 0 accuracy; ~0 spread at 100 accuracy

_id_counter = itertools.count(1)


class Projectile:
    def __init__(self, x, y, direction, owner_id, damage):
        self.id = f"proj_{next(_id_counter)}"
        self.x = x
        self.y = y
        self.direction = direction
        self.owner_id = owner_id
        self.damage = damage
        self.alive = True

    def update(self, dt, arena_width, arena_height):
        rad = math.radians(self.direction)
        self.x += math.cos(rad) * PROJECTILE_SPEED * dt
        self.y += math.sin(rad) * PROJECTILE_SPEED * dt
        if self.x < 0 or self.x > arena_width or self.y < 0 or self.y > arena_height:
            self.alive = False

    def to_dict(self):
        return {
            "id": self.id,
            "x": round(self.x, 1),
            "y": round(self.y, 1),
            "direction": round(self.direction, 1),
            "owner_id": self.owner_id,
        }


def spawn_projectile(shooter, rng=random):
    """Fires a projectile from `shooter`, applying accuracy-based spread."""
    accuracy = shooter.build["accuracy"]
    spread = ACCURACY_MAX_SPREAD_DEGREES * (1 - accuracy / 100.0)
    direction = shooter.direction + rng.uniform(-spread, spread)
    damage = compute_damage(shooter.build["weapon_power"])
    return Projectile(shooter.x, shooter.y, direction, shooter.id, damage)


def compute_damage(weapon_power):
    return BASE_DAMAGE + weapon_power * DAMAGE_PER_WEAPON_POINT


def apply_armor_reduction(raw_damage, armor):
    reduction = min(MAX_ARMOR_REDUCTION, armor * ARMOR_REDUCTION_PER_POINT)
    return raw_damage * (1 - reduction)


def resolve_collisions(projectiles, robots):
    """Applies damage/destruction for any projectile touching a live robot.

    Returns (surviving_projectiles, events) — events are dicts matching the
    `hit` / `destroyed` shapes in docs/ARCHITECTURE.md section 1.
    """
    events = []
    surviving = []

    for proj in projectiles:
        if not proj.alive:
            continue

        target = next(
            (r for r in robots
             if r.alive and r.id != proj.owner_id
             and distance(proj.x, proj.y, r.x, r.y) <= PROJECTILE_RADIUS + ROBOT_RADIUS),
            None,
        )

        if target is None:
            surviving.append(proj)
            continue

        final_damage = apply_armor_reduction(proj.damage, target.build["armor"])
        target.apply_damage(final_damage)
        target.damage_received += final_damage

        attacker = next((r for r in robots if r.id == proj.owner_id), None)
        if attacker is not None:
            attacker.hits_landed += 1
            attacker.damage_caused += final_damage

        events.append({
            "type": "hit",
            "target_id": target.id,
            "attacker_id": proj.owner_id,
            "damage": round(final_damage, 1),
        })
        if not target.alive:
            if attacker is not None:
                attacker.kills += 1
            events.append({"type": "destroyed", "robot_id": target.id})

    return surviving, events


def distance(x1, y1, x2, y2):
    return math.hypot(x1 - x2, y1 - y2)
