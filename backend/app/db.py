"""SQLite persistence layer: users, robots, robot versions, matches, round
results, and derived wins/leaderboard scores.

GitHub issue #4. Independent of the simulation — only needs the shapes in
docs/ARCHITECTURE.md.
"""

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).parent / "botforge.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS robots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    name TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS robot_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    robot_id INTEGER NOT NULL REFERENCES robots(id),
    version INTEGER NOT NULL,
    definition_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (robot_id, version)
);

CREATE TABLE IF NOT EXISTS matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finished_at TEXT
);

CREATE TABLE IF NOT EXISTS match_participants (
    match_id INTEGER NOT NULL REFERENCES matches(id),
    robot_version_id INTEGER NOT NULL REFERENCES robot_versions(id),
    PRIMARY KEY (match_id, robot_version_id)
);

CREATE TABLE IF NOT EXISTS round_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id INTEGER NOT NULL REFERENCES matches(id),
    round_number INTEGER NOT NULL,
    winner_robot_version_id INTEGER REFERENCES robot_versions(id),
    survivors_json TEXT NOT NULL,
    duration_seconds REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS round_points (
    round_result_id INTEGER NOT NULL REFERENCES round_results(id),
    robot_version_id INTEGER NOT NULL REFERENCES robot_versions(id),
    points INTEGER NOT NULL,
    PRIMARY KEY (round_result_id, robot_version_id)
);

CREATE TABLE IF NOT EXISTS match_stats (
    match_id INTEGER NOT NULL REFERENCES matches(id),
    robot_version_id INTEGER NOT NULL REFERENCES robot_versions(id),
    damage_caused REAL NOT NULL DEFAULT 0,
    damage_received REAL NOT NULL DEFAULT 0,
    shots_fired INTEGER NOT NULL DEFAULT 0,
    hits_landed INTEGER NOT NULL DEFAULT 0,
    kills INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (match_id, robot_version_id)
);
"""


@contextmanager
def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with _connect() as conn:
        conn.executescript(SCHEMA)


def get_or_create_user(username):
    with _connect() as conn:
        row = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        if row:
            return row["id"]
        cur = conn.execute("INSERT INTO users (username) VALUES (?)", (username,))
        return cur.lastrowid


def save_robot_version(username, robot_definition):
    """Stores an uploaded robot JSON, creating the robot record on first
    upload for this (username, name) pair.

    Returns (robot_id, version_number, robot_version_id).
    """
    user_id = get_or_create_user(username)
    name = robot_definition["name"]

    with _connect() as conn:
        row = conn.execute(
            "SELECT id FROM robots WHERE user_id = ? AND name = ?", (user_id, name)
        ).fetchone()
        if row:
            robot_id = row["id"]
        else:
            cur = conn.execute("INSERT INTO robots (user_id, name) VALUES (?, ?)", (user_id, name))
            robot_id = cur.lastrowid

        last = conn.execute(
            "SELECT MAX(version) AS v FROM robot_versions WHERE robot_id = ?", (robot_id,)
        ).fetchone()
        next_version = (last["v"] or 0) + 1

        cur = conn.execute(
            "INSERT INTO robot_versions (robot_id, version, definition_json) VALUES (?, ?, ?)",
            (robot_id, next_version, json.dumps(robot_definition)),
        )
        robot_version_id = cur.lastrowid

    return robot_id, next_version, robot_version_id


def create_match(robot_version_ids):
    with _connect() as conn:
        cur = conn.execute("INSERT INTO matches (status) VALUES ('running')")
        match_id = cur.lastrowid
        conn.executemany(
            "INSERT INTO match_participants (match_id, robot_version_id) VALUES (?, ?)",
            [(match_id, rv_id) for rv_id in robot_version_ids],
        )
    return match_id


def record_round_result(match_id, round_result, robot_version_lookup):
    """`robot_version_lookup` maps in-arena robot_id -> robot_version_id
    for every participant in the match (not just the winner)."""
    winner_version_id = (
        robot_version_lookup.get(round_result.winner_id) if round_result.winner_id else None
    )
    with _connect() as conn:
        cur = conn.execute(
            """INSERT INTO round_results
               (match_id, round_number, winner_robot_version_id, survivors_json, duration_seconds)
               VALUES (?, ?, ?, ?, ?)""",
            (
                match_id,
                round_result.round_number,
                winner_version_id,
                json.dumps(round_result.survivors),
                round_result.duration,
            ),
        )
        round_result_id = cur.lastrowid
        conn.executemany(
            "INSERT INTO round_points (round_result_id, robot_version_id, points) VALUES (?, ?, ?)",
            [
                (round_result_id, robot_version_lookup[arena_id], points)
                for arena_id, points in round_result.points_awarded.items()
                if arena_id in robot_version_lookup
            ],
        )


def finish_match(match_id):
    with _connect() as conn:
        conn.execute(
            "UPDATE matches SET status = 'finished', finished_at = CURRENT_TIMESTAMP WHERE id = ?",
            (match_id,),
        )


def record_match_stats(match_id, robot_version_lookup, robots):
    """Persists cumulative per-robot match stats (damage/accuracy/kills)
    for the leaderboard. `robots` are the arena Robot objects that just
    finished the match; `robot_version_lookup` maps their arena id to a
    robot_version_id, same as record_round_result."""
    rows = [
        (
            match_id,
            robot_version_lookup[robot.id],
            robot.damage_caused,
            robot.damage_received,
            robot.shots_fired,
            robot.hits_landed,
            robot.kills,
        )
        for robot in robots
        if robot.id in robot_version_lookup
    ]
    with _connect() as conn:
        conn.executemany(
            """INSERT INTO match_stats
               (match_id, robot_version_id, damage_caused, damage_received, shots_fired, hits_landed, kills)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            rows,
        )


def get_leaderboard(limit=50):
    """Aggregates per-robot stats (summed across all of that robot's
    uploaded versions) into the row shape frontend/src/leaderboard.js
    already renders (see frontend/src/mock/leaderboard.mock.json)."""
    query = """
        SELECT
            r.id AS robot_id,
            r.name AS robot_name,
            u.username AS creator,
            (
                SELECT COUNT(DISTINCT mp.match_id)
                FROM match_participants mp
                JOIN robot_versions rv ON rv.id = mp.robot_version_id
                WHERE rv.robot_id = r.id
            ) AS matches,
            (
                SELECT COUNT(*)
                FROM round_results rr
                JOIN robot_versions rv ON rv.id = rr.winner_robot_version_id
                WHERE rv.robot_id = r.id
            ) AS rounds_won,
            (
                SELECT COUNT(*)
                FROM round_results rr
                JOIN match_participants mp ON mp.match_id = rr.match_id
                JOIN robot_versions rv ON rv.id = mp.robot_version_id
                WHERE rv.robot_id = r.id
                  AND rr.winner_robot_version_id IS NOT NULL
                  AND rr.winner_robot_version_id != rv.id
            ) AS rounds_lost,
            COALESCE((
                SELECT SUM(ms.damage_caused)
                FROM match_stats ms
                JOIN robot_versions rv ON rv.id = ms.robot_version_id
                WHERE rv.robot_id = r.id
            ), 0) AS damage_caused,
            COALESCE((
                SELECT SUM(ms.damage_received)
                FROM match_stats ms
                JOIN robot_versions rv ON rv.id = ms.robot_version_id
                WHERE rv.robot_id = r.id
            ), 0) AS damage_received,
            COALESCE((
                SELECT SUM(ms.shots_fired)
                FROM match_stats ms
                JOIN robot_versions rv ON rv.id = ms.robot_version_id
                WHERE rv.robot_id = r.id
            ), 0) AS shots_fired,
            COALESCE((
                SELECT SUM(ms.hits_landed)
                FROM match_stats ms
                JOIN robot_versions rv ON rv.id = ms.robot_version_id
                WHERE rv.robot_id = r.id
            ), 0) AS hits_landed,
            COALESCE((
                SELECT SUM(ms.kills)
                FROM match_stats ms
                JOIN robot_versions rv ON rv.id = ms.robot_version_id
                WHERE rv.robot_id = r.id
            ), 0) AS kills
        FROM robots r
        JOIN users u ON u.id = r.user_id
    """
    with _connect() as conn:
        rows = [dict(row) for row in conn.execute(query).fetchall()]

    for row in rows:
        decided = row["rounds_won"] + row["rounds_lost"]
        row["win_pct"] = (row["rounds_won"] / decided) if decided else 0.0
        row["accuracy"] = (row["hits_landed"] / row["shots_fired"]) if row["shots_fired"] else 0.0
        del row["shots_fired"]
        del row["hits_landed"]

    rows.sort(key=lambda r: (r["rounds_won"], r["win_pct"]), reverse=True)
    for rank, row in enumerate(rows[:limit], start=1):
        row["rank"] = rank

    return rows[:limit]
