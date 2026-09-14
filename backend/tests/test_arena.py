from app.arena import Arena
from app.robot import Robot

BUILD = {"speed": 0, "armor": 0, "weapon_power": 25, "accuracy": 100, "fire_rate": 10, "sensor_range": 10}
SHOOT_LOGIC = [{"priority": 1, "if": {"op": "eq", "left": 1, "right": 1}, "then": "shoot"}]


def make_shooter(robot_id, x, y):
    return Robot(robot_id, robot_id, x, y, direction=0, build=dict(BUILD), logic=SHOOT_LOGIC)


def test_shot_is_blocked_when_shooter_has_no_energy():
    shooter = make_shooter("shooter", 0, 0)
    target = make_shooter("target", 400, 0)
    target.logic = []
    shooter.energy = 0.0
    arena = Arena([shooter, target])

    arena.tick(dt=0.1)

    # Energy regenerates a little (0.1s worth) but the shot's cost is
    # never deducted, since it never actually fired.
    assert shooter.energy < 8.0  # far less than SHOOT_ENERGY_COST
    assert len(arena.projectiles) == 0


def test_shot_consumes_energy_only_when_it_actually_fires():
    shooter = make_shooter("shooter", 0, 0)
    target = make_shooter("target", 400, 0)
    target.logic = []
    energy_before = shooter.energy

    arena = Arena([shooter, target])
    arena.tick(dt=0.1)

    assert len(arena.projectiles) == 1
    assert shooter.energy < energy_before


def test_energy_does_not_collapse_from_being_on_cooldown():
    # Regression check: selecting "shoot" every tick while the weapon is
    # still on cooldown must NOT repeatedly drain energy — only an actual
    # shot (cooldown ready AND enough energy) should cost anything.
    shooter = make_shooter("shooter", 0, 0)
    target = make_shooter("target", 400, 0)
    target.logic = []
    arena = Arena([shooter, target])

    dt = 1 / 20
    for _ in range(10):  # well within a single fire_cooldown window
        arena.tick(dt)

    assert len(arena.projectiles) == 1  # only the first tick's shot fired
    assert shooter.energy > 0  # energy wasn't repeatedly charged while on cooldown
