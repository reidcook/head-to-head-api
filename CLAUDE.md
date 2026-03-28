# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
uv run fastapi dev api/server.py   # Dev server at localhost:8000 (hot reload)
uv run fastapi run api/server.py   # Production server
```

The project uses `uv` for dependency management. Dependencies are declared in `pyproject.toml` (Python >= 3.13).

## Architecture

FastAPI async server backed by **MongoDB Atlas** via the **Motor** async driver. All data is multi-tenant, scoped by a `groupId` field on every document. The frontend uses `"group1"` as the group.

### Entry point

`api/server.py` — creates the FastAPI app, registers all routers, configures CORS (allow all origins), and registers global exception handlers for `RequestValidationError` and `ValueError` (both return HTTP 400).

### Routers

Each domain has its own file with a router that gets `include_router`'d in `server.py`:

| File | Router | Prefix pattern |
|------|--------|----------------|
| `api/players.py` | `player_router` | `/players/...` |
| `api/matches.py` | `match_router` | `/matches/...` |
| `api/tournaments.py` | `tournament_router` | `/tournaments/...` |
| `api/overview.py` | `overview_router` | `/overview/{groupId}/...` |

### Database

- `api/dependencies/mongo.py` — async Motor client initialized in a FastAPI `lifespan` context manager. `get_database()` is a FastAPI dependency injected into route handlers.
- Connection string comes from the `MONGODB_URI` environment variable (loaded via `dotenv`).
- The database name is embedded in the connection string (Motor calls `get_database()` on the client which uses the database specified in the URI).
- Collections: `players`, `matches`, `tournaments`

### Data models (Pydantic)

All models use `extra = "allow"` to accept additional fields. MongoDB `_id` is serialized to a string via `serialize_doc()` in `api/utils.py`.

**Player** (`api/players.py`):
```
name, character, debut (tournament name), image (base64), details, groupId
```

**Match** (`api/matches.py`):
```
player1, player2, winner (must equal player1 or player2), tournament, groupId
```
- Validators enforce `player1 != player2` and `winner in {player1, player2}`.

**Tournament** (`api/tournaments.py`):
```
name, winner (must be an existing player name), date, url, groupId
```
- Date format: `"MM-dd-yyyy"` (string, no DB-level enforcement — parse with `datetime.strptime(date_str, "%m-%d-%Y")`).

### Referential integrity

Enforced at the application layer (not the database):
- Creating a player requires the `debut` tournament to already exist.
- Creating/updating a match requires both players and the tournament to exist.
- Creating/updating a tournament requires the `winner` player to exist.

### Overview endpoints (`api/overview.py`)

Stats-only read endpoints that compute derived data on the fly from the DB:
- `GET /overview/{groupId}/summary` — total counts for players, matches, tournaments
- `GET /overview/{groupId}/players_by_win_rate` — players sorted by win % desc
- `GET /overview/{groupId}/players_by_tournament_wins` — players sorted by tournament wins desc
- `GET /overview/{groupId}/players_by_match_wins` — players sorted by match wins desc
- `GET /overview/{groupId}/tournaments` — all tournaments sorted by date desc (newest first)
- `GET /overview/{groupId}/tournaments_per_year` — `{year, count}` list sorted by year asc

### Utilities

- `api/utils.py` — `serialize_doc(doc)` converts a MongoDB document dict (stringifying `_id`); also contains `SMASH_CHARS` list of all playable Super Smash Bros. Ultimate characters.
- `api/admin_config.py` — `FieldConfig` Pydantic model used by the frontend admin page to dynamically generate forms.

### Interactive API docs

FastAPI auto-generates docs at `http://localhost:8000/docs` (Swagger UI) and `http://localhost:8000/redoc` when the dev server is running.
