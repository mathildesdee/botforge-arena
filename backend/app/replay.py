"""Records a round's tick-by-tick game_state stream plus a handful of
notable-moment markers, so the browser can replay it later instead of
only ever watching live.

PDF section 28 ("Replay mode"): "save game events... a timeline could
allow them to jump to: First contact. First hit. Robot below 50%
health. Robot below 20% health. Final kill."

Pure/standalone, like match.py — no FastAPI or persistence dependency.
main.py owns persisting the result via db.save_replay().
"""

HEALTH_MARKER_THRESHOLDS = (50, 20)


class Recorder:
    def __init__(self):
        self.frames = []
        self.markers = {"first_shot": None, "first_hit": None, "final_kill": None}
        # {robot_id: {"below_50": tick|None, "below_20": tick|None}}
        self.health_markers = {}

    def record(self, state):
        """Appends one game_state dict (as broadcast) to the recording
        and updates the notable-moment markers from it."""
        self.frames.append(state)
        tick = state["tick"]

        if self.markers["first_shot"] is None and state.get("projectiles"):
            self.markers["first_shot"] = tick

        for event in state.get("events", []):
            if event["type"] == "hit" and self.markers["first_hit"] is None:
                self.markers["first_hit"] = tick
            if event["type"] == "destroyed":
                self.markers["final_kill"] = tick  # last destruction wins

        for robot in state.get("robots", []):
            thresholds = self.health_markers.setdefault(
                robot["id"], {f"below_{t}": None for t in HEALTH_MARKER_THRESHOLDS},
            )
            pct = (robot["health"] / robot["max_health"] * 100.0) if robot["max_health"] else 0.0
            for t in HEALTH_MARKER_THRESHOLDS:
                key = f"below_{t}"
                if thresholds[key] is None and pct < t:
                    thresholds[key] = tick

    def to_dict(self):
        return {
            "frames": self.frames,
            "markers": dict(self.markers),
            "health_markers": {rid: dict(v) for rid, v in self.health_markers.items()},
        }
