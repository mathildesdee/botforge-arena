"""Automatic round-robin tournament: schedules every pairing among the
participants, runs each pairing as a full Match, and produces a final
ranking across all pairings.

Milestone 10 (Tournament System) from BotForge Arena.pdf: "Automatically
schedule many robots against each other. Run matches. Calculate
results. Produce the final leaderboard." Every pairing is a 1v1 match
(the tournament examples in the PDF are always pairwise), run several
rounds like any other match.

Pure/standalone, like match.py — no FastAPI or WebSocket dependency.
"""

import itertools

from .match import DEFAULT_NUM_ROUNDS, DEFAULT_ROUND_TIME_LIMIT, Match
from .robot import Robot


class Participant:
    """A tournament entrant: identity + the robot definition used to
    build a fresh Robot for each pairing (a robot must start each
    pairing undamaged, independent of any previous pairing)."""

    def __init__(self, participant_id, name, build, logic, variables=None, robot_version_id=None):
        self.id = participant_id
        self.name = name
        self.build = build
        self.logic = logic
        self.variables = variables
        self.robot_version_id = robot_version_id

    def new_robot(self):
        return Robot(self.id, self.name, x=0, y=0, direction=0,
                      build=self.build, logic=self.logic, variables=self.variables)


class PairingResult:
    def __init__(self, pairing_number, participant_ids, match_result):
        self.pairing_number = pairing_number
        self.participant_ids = participant_ids
        self.match_result = match_result  # Match.final_result()

    def to_dict(self):
        return {
            "pairing": self.pairing_number,
            "participants": self.participant_ids,
            "result": self.match_result,
        }


class Tournament:
    def __init__(self, participants, num_rounds=DEFAULT_NUM_ROUNDS,
                 round_time_limit=DEFAULT_ROUND_TIME_LIMIT, rng=None):
        self.participants = participants
        self.num_rounds = num_rounds
        self.round_time_limit = round_time_limit
        self.rng = rng

        self.pairings = list(itertools.combinations(participants, 2))
        self.pairing_results = []
        self.current_pairing_index = 0
        self.current_match = None
        self.finished = len(self.pairings) == 0

    def start_next_pairing(self):
        """Builds a fresh Match for the next scheduled pairing and returns
        the (participant_a, participant_b) tuple, or None if every
        pairing has already run."""
        if self.current_pairing_index >= len(self.pairings):
            self.finished = True
            self.current_match = None
            return None

        a, b = self.pairings[self.current_pairing_index]
        robots = [a.new_robot(), b.new_robot()]
        self.current_match = Match(
            robots, num_rounds=self.num_rounds, round_time_limit=self.round_time_limit, rng=self.rng,
        )
        return a, b

    def finish_current_pairing(self):
        """Call once `self.current_match.finished` is True. Records the
        pairing's result and advances to the next one."""
        a, b = self.pairings[self.current_pairing_index]
        result = PairingResult(
            pairing_number=self.current_pairing_index + 1,
            participant_ids=[a.id, b.id],
            match_result=self.current_match.final_result(),
        )
        self.pairing_results.append(result)
        self.current_pairing_index += 1
        self.current_match = None
        if self.current_pairing_index >= len(self.pairings):
            self.finished = True

    def run_to_completion(self, dt):
        """Drives every pairing to completion without any real-time
        pacing — for tests, or a future fast "simulation mode"."""
        while not self.finished:
            if self.start_next_pairing() is None:
                break
            match = self.current_match
            while not match.finished:
                match.start_round()
                while True:
                    result = match.tick(dt)
                    if result["round_result"] is not None:
                        break
            self.finish_current_pairing()
        return self.standings()

    def standings(self):
        """Aggregates each participant's total points across every
        pairing they played, sorted descending."""
        totals = {p.id: 0 for p in self.participants}
        for pairing_result in self.pairing_results:
            for participant_id, points in pairing_result.match_result["scores"].items():
                totals[participant_id] += points

        ranking = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)
        return {
            "totals": totals,
            "ranking": [{"participant_id": pid, "points": pts} for pid, pts in ranking],
            "pairings": [r.to_dict() for r in self.pairing_results],
        }
