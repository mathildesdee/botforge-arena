from app.replay import Recorder


def frame(tick, robots, projectiles=None, events=None):
    return {
        "type": "game_state",
        "tick": tick,
        "robots": robots,
        "projectiles": projectiles or [],
        "events": events or [],
    }


def robot_dict(robot_id, health, max_health=100):
    return {"id": robot_id, "name": robot_id, "x": 0, "y": 0, "direction": 0,
            "health": health, "max_health": max_health, "energy": 100, "alive": health > 0}


def test_records_every_frame_in_order():
    recorder = Recorder()
    recorder.record(frame(1, [robot_dict("a", 100)]))
    recorder.record(frame(2, [robot_dict("a", 100)]))

    result = recorder.to_dict()
    assert [f["tick"] for f in result["frames"]] == [1, 2]


def test_first_shot_marker_is_set_on_first_frame_with_a_projectile():
    recorder = Recorder()
    recorder.record(frame(1, [robot_dict("a", 100)]))
    recorder.record(frame(2, [robot_dict("a", 100)], projectiles=[{"id": "p1"}]))
    recorder.record(frame(3, [robot_dict("a", 100)], projectiles=[{"id": "p2"}]))

    markers = recorder.to_dict()["markers"]
    assert markers["first_shot"] == 2  # not 3 — first occurrence wins


def test_first_hit_marker_is_set_once():
    recorder = Recorder()
    recorder.record(frame(1, [robot_dict("a", 100)], events=[{"type": "hit", "target_id": "a", "damage": 10}]))
    recorder.record(frame(2, [robot_dict("a", 90)], events=[{"type": "hit", "target_id": "a", "damage": 10}]))

    markers = recorder.to_dict()["markers"]
    assert markers["first_hit"] == 1


def test_final_kill_marker_tracks_the_last_destruction():
    recorder = Recorder()
    recorder.record(frame(5, [robot_dict("a", 0)], events=[{"type": "destroyed", "robot_id": "a"}]))
    recorder.record(frame(9, [robot_dict("b", 0)], events=[{"type": "destroyed", "robot_id": "b"}]))

    markers = recorder.to_dict()["markers"]
    assert markers["final_kill"] == 9


def test_health_markers_track_the_first_tick_below_each_threshold():
    recorder = Recorder()
    recorder.record(frame(1, [robot_dict("a", 100)]))
    recorder.record(frame(2, [robot_dict("a", 45)]))  # crosses below 50
    recorder.record(frame(3, [robot_dict("a", 15)]))  # crosses below 20
    recorder.record(frame(4, [robot_dict("a", 10)]))  # still below 20 — marker shouldn't move

    health_markers = recorder.to_dict()["health_markers"]
    assert health_markers["a"] == {"below_50": 2, "below_20": 3}


def test_robot_that_never_drops_low_has_no_health_markers_set():
    recorder = Recorder()
    recorder.record(frame(1, [robot_dict("a", 100)]))
    recorder.record(frame(2, [robot_dict("a", 80)]))

    health_markers = recorder.to_dict()["health_markers"]
    assert health_markers["a"] == {"below_50": None, "below_20": None}
