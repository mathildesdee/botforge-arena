"""Round & match management: N rounds per match, each capped at a time
limit, with win/draw scoring.

GitHub issue #7. Built against the game_state/event shapes in
docs/ARCHITECTURE.md; uses a stubbed-simple Arena tick until combat/logic
are tuned further.
"""

import random

from .arena import Arena

DEFAULT_NUM_ROUNDS = 10
DEFAULT_ROUND_TIME_LIMIT = 60.0
WIN_POINTS = 3
SURVIVAL_POINTS = 1


class RoundResult:
    def __init__(self, round_number, winner_id, survivors, points_awarded, duration):
        self.round_number = round_number
        self.winner_id = winner_id
        self.survivors = survivors
        self.points_awarded = points_awarded
        self.duration = duration

    def to_dict(self):
        return {
            "round": self.round_number,
            "winner_id": self.winner_id,
            "survivors": self.survivors,
            "points_awarded": self.points_awarded,
            "duration": round(self.duration, 1),
        }


class Match:
    """Owns one Arena and drives it through `num_rounds` rounds, tallying
    per-round scores into a final match result."""

    def __init__(self, robots, num_rounds=DEFAULT_NUM_ROUNDS,
                 round_time_limit=DEFAULT_ROUND_TIME_LIMIT, rng=None):
        self.arena = Arena(robots)
        self.num_rounds = num_rounds
        self.round_time_limit = round_time_limit
        self.rng = rng or random.Random()

        self.scores = {r.id: 0 for r in robots}
        self.round_results = []
        self.current_round = 0
        self.round_elapsed = 0.0
        self.finished = False

    def start_round(self):
        self.current_round += 1
        self.round_elapsed = 0.0
        self.arena.randomize_spawns(rng=self.rng)

    def tick(self, dt):
        """Advances the current round by `dt`. Always returns a dict with
        this tick's combat `events` (for game_state broadcasting) and a
        `round_result` (a RoundResult, or None if the round is still going).
        """
        if self.finished:
            return {"events": [], "round_result": None}

        events = self.arena.tick(dt)
        self.round_elapsed += dt

        alive = [r for r in self.arena.robots if r.alive]
        round_result = None
        if len(alive) <= 1 or self.round_elapsed >= self.round_time_limit - 1e-9:
            round_result = self._end_round(alive)

        return {"events": events, "round_result": round_result}

    def _end_round(self, alive):
        if len(alive) == 1:
            winner_id = alive[0].id
            points_awarded = {winner_id: WIN_POINTS}
        elif len(alive) > 1:
            winner_id = None
            points_awarded = {r.id: SURVIVAL_POINTS for r in alive}
        else:
            winner_id = None
            points_awarded = {}

        for robot_id, points in points_awarded.items():
            self.scores[robot_id] += points

        result = RoundResult(
            round_number=self.current_round,
            winner_id=winner_id,
            survivors=[r.id for r in alive],
            points_awarded=points_awarded,
            duration=self.round_elapsed,
        )
        self.round_results.append(result)

        if self.current_round >= self.num_rounds:
            self.finished = True

        return result

    def final_result(self):
        ranking = sorted(self.scores.items(), key=lambda kv: kv[1], reverse=True)
        return {
            "scores": dict(self.scores),
            "ranking": [{"robot_id": rid, "points": pts} for rid, pts in ranking],
            "rounds": [r.to_dict() for r in self.round_results],
        }

    def run_to_completion(self, dt):
        """Drives every remaining round to completion without any
        real-time pacing — for headless bulk simulation (PDF section 29,
        "Simulation mode") or tests."""
        while not self.finished:
            self.start_round()
            while True:
                result = self.tick(dt)
                if result["round_result"] is not None:
                    break
        return self.final_result()

    def round_win_counts(self):
        """{robot_id: rounds that robot won} plus a "draws" count for
        rounds with no single winner (survival draw or mutual
        destruction) — the tally "Simulation mode" reports."""
        counts = {r.id: 0 for r in self.arena.robots}
        counts["draws"] = 0
        for round_result in self.round_results:
            if round_result.winner_id is not None:
                counts[round_result.winner_id] += 1
            else:
                counts["draws"] += 1
        return counts
