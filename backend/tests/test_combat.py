import random

from app import combat
from app.robot import Robot

BUILD = {"speed": 10, "armor": 0, "weapon_power": 50, "accuracy": 100, "fire_rate": 10, "sensor_range": 10}


def make_robot(robot_id, x, y):
    return Robot(robot_id, robot_id, x, y, direction=0, build=dict(BUILD), logic=[])


def test_projectile_hits_robot_in_its_path():
    shooter = make_robot("shooter", 0, 0)
    target = make_robot("target", 20, 0)
    proj = combat.spawn_projectile(shooter, rng=random.Random(0))

    surviving, events = combat.resolve_collisions([proj], [shooter, target])

    assert any(e["type"] == "hit" and e["target_id"] == "target" for e in events)
    assert target.health < target.max_health


def test_projectile_ignores_its_owner():
    shooter = make_robot("shooter", 0, 0)
    proj = combat.Projectile(x=0, y=0, direction=0, owner_id="shooter", damage=10)

    surviving, events = combat.resolve_collisions([proj], [shooter])

    assert events == []
    assert proj in surviving


def test_destruction_event_fires_at_zero_health():
    shooter = make_robot("shooter", 0, 0)
    target = make_robot("target", 5, 0)
    target.health = 1

    proj = combat.Projectile(x=0, y=0, direction=0, owner_id="shooter", damage=999)
    surviving, events = combat.resolve_collisions([proj], [shooter, target])

    assert not target.alive
    assert any(e["type"] == "destroyed" and e["robot_id"] == "target" for e in events)


def test_armor_reduces_damage():
    low_armor_target = make_robot("low", 5, 0)
    high_armor_target = make_robot("high", 5, 0)
    low_armor_target.build = {**BUILD, "armor": 0}
    high_armor_target.build = {**BUILD, "armor": 100}

    proj1 = combat.Projectile(x=0, y=0, direction=0, owner_id="x", damage=20)
    proj2 = combat.Projectile(x=0, y=0, direction=0, owner_id="x", damage=20)

    combat.resolve_collisions([proj1], [low_armor_target])
    combat.resolve_collisions([proj2], [high_armor_target])

    assert high_armor_target.health > low_armor_target.health


def test_out_of_bounds_projectile_is_removed():
    proj = combat.Projectile(x=-5, y=10, direction=180, owner_id="shooter", damage=5)
    proj.update(dt=0.1, arena_width=800, arena_height=600)
    assert not proj.alive
