# BotForge Arena

A multiplayer browser game where players build robots, give them a limited set of upgrade points, program their behaviour with JSON logic, and then watch them fight automatically. No one controls a robot during battle — only the logic programmed beforehand decides what it does.

Think "a small RoboCode", presented as a polished browser game.

## Stack

- **Backend:** Python, FastAPI, WebSockets, SQLite — the server is authoritative over game state.
- **Frontend:** JavaScript, Phaser — renders whatever the server sends, never decides outcomes itself.

## Project layout

```
backend/    FastAPI app: game simulation, robot interpreter, persistence
frontend/   Phaser app: arena rendering, robot builder, lobby, leaderboard
docs/       Architecture and shared data contracts
```

## Getting started

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the data contracts both sides build against (robot state shape, WebSocket protocol, robot JSON program schema) before touching code.

## Running it locally

Two servers, in two terminals.

**Backend** (from `backend/`):

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Frontend** (from `frontend/`, a separate terminal — it's a static site, needs to be served over http, not opened as a `file://` URL):

```
python3 -m http.server 8642
```

Then open `http://localhost:8642/lobby.html` in the browser.

### Try the full flow

1. In the Lobby, pick a name and click **Join**.
2. You need a robot: open a second tab to `builder.html`, fill in a robot name + your name + spend the 100 build points, then **Download JSON**.
3. Back in the Lobby, upload that JSON file, then click **Mark ready**.
4. Open a second browser tab (or ask whoever you're playing with to open the same `lobby.html` URL on their machine, same Wi-Fi) and repeat steps 1-3 with a different name — at least 2 ready players are required to start.
5. Once both are ready, either player clicks **Start match**.
6. Open `index.html` (the Arena) to watch the battle live — everyone connected spectates together, whether they played or not.
7. After the match, check `leaderboard.html` for updated stats.

`backend/app/main.py` is the single source of truth while testing — if something in the frontend looks wrong, check what it actually sent/received over `/ws` rather than assuming.

## Working process

This project is deliberately built in small, understandable steps — see the open issues for the current task breakdown. Each issue is scoped so two people can work in parallel without blocking on each other, by building against the contracts in `docs/ARCHITECTURE.md` rather than against each other's in-progress code.
