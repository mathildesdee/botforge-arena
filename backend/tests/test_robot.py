from app.robot import Robot

BUILD = {"speed": 20, "armor": 15, "weapon_power": 25, "accuracy": 20, "fire_rate": 10, "sensor_range": 10}


def make_robot(x=100, y=100, direction=0):
    return Robot("r1", "Hunter", x, y, direction, dict(BUILD), logic=[])


def test_holds_position_direction_and_build_derived_stats():
    robot = make_robot(x=50, y=60, direction=90)
    assert (robot.x, robot.y, robot.direction) == (50, 60, 90)
    assert robot.health == robot.max_health == 100.0
    assert robot.energy == robot.max_energy == 100.0
    assert robot.build["armor"] == 15
    # speed, fire_cooldown (fire-rate) and sensor_range are all derived from build points.
    assert robot.speed > 0
    assert robot.fire_cooldown > 0
    assert robot.sensor_range > 0


def test_taking_damage_reduces_health():
    robot = make_robot()
    robot.apply_damage(30)
    assert robot.health == 70.0
    assert robot.alive is True


def test_health_can_never_go_below_zero():
    robot = make_robot()
    robot.apply_damage(9999)
    assert robot.health == 0.0
    assert robot.alive is False

    # Further damage after death is a no-op, not a negative health value.
    robot.apply_damage(50)
    assert robot.health == 0.0


def test_movement_updates_position_and_direction_correctly():
    robot = make_robot(x=100, y=100, direction=0)
    robot.move_forward(dt=1.0, arena_width=800, arena_height=600)
    # Facing 0 degrees (+x axis): moving forward increases x, leaves y unchanged.
    assert robot.x > 100
    assert round(robot.y, 6) == 100

    start_direction = robot.direction
    robot.turn_right(dt=1.0, degrees_per_second=90.0)
    assert robot.direction == (start_direction + 90.0) % 360.0

    robot.direction = 0.0
    x_before_backward = robot.x
    robot.move_backward(dt=1.0, arena_width=800, arena_height=600)
    # Backward motion at heading 0 moves in -x, without changing the facing direction.
    assert robot.x < x_before_backward
    assert robot.direction == 0.0


def test_energy_regenerates_up_to_the_cap():
    robot = make_robot()
    robot.energy = 50.0
    robot.regenerate_energy(dt=1.0)
    assert robot.energy == 58.0  # ENERGY_REGEN_PER_SECOND = 8.0

    robot.energy = robot.max_energy - 1.0
    robot.regenerate_energy(dt=10.0)
    assert robot.energy == robot.max_energy  # never exceeds the cap


def test_try_consume_energy_succeeds_and_fails_appropriately():
    robot = make_robot()
    robot.energy = 10.0

    assert robot.try_consume_energy(6.0) is True
    assert robot.energy == 4.0

    assert robot.try_consume_energy(6.0) is False
    assert robot.energy == 4.0  # unchanged when there wasn't enough


def test_variables_default_to_empty_and_are_stored_as_given():
    robot = make_robot()
    assert robot.variables == {}

    robot2 = Robot("r2", "Named", 0, 0, 0, dict(BUILD), logic=[], variables={"aggression": 70})
    assert robot2.variables == {"aggression": 70}


def test_memory_defaults_and_respawn_resets_it():
    robot = make_robot()
    assert robot.last_enemy_position is None
    assert robot.seconds_since_enemy_seen == float("inf")
    assert robot.previous_health_pct() == 100.0

    robot.last_enemy_position = (123, 456)
    robot.seconds_since_enemy_seen = 3.0
    robot.previous_health = 40.0

    robot.respawn(x=10, y=10)

    assert robot.last_enemy_position is None
    assert robot.seconds_since_enemy_seen == float("inf")
    assert robot.previous_health_pct() == 100.0
