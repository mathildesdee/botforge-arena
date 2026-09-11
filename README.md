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

## Working process

This project is deliberately built in small, understandable steps — see the open issues for the current task breakdown. Each issue is scoped so two people can work in parallel without blocking on each other, by building against the contracts in `docs/ARCHITECTURE.md` rather than against each other's in-progress code.
