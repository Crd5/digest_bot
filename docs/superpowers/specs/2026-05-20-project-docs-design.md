# Project Documentation Design

## Goal

Create a dedicated `docs/` documentation hub for developers and future agents while tightening `README.md` and `GEMINI.md` into concise entry points.

## Scope

This documentation pass will add a compact docs set:

- `docs/index.md`: table of contents and reading order.
- `docs/development.md`: local setup, environment variables, dependency installation, test command, and safe development workflow.
- `docs/architecture.md`: runtime architecture, command handlers, digest flow, cursor semantics, Gemini summarization, Telegram message splitting, and SQLite persistence.
- `docs/operations.md`: first-run Telegram authentication, systemd service generation, generated private files, file permissions, scheduling, troubleshooting, and backup guidance.
- `docs/agent-notes.md`: high-signal constraints and invariants for future coding agents.

The pass will also update:

- `README.md`: human-facing quickstart with links into `docs/`.
- `GEMINI.md`: short future-agent quickstart with project map, invariants, and links into `docs/`.

## Architecture And Content Model

The docs will use Markdown only and stay close to the repository's current structure. The public-facing setup and command reference remains in `README.md`; deeper behavior, operations, and agent workflow content moves into `docs/`.

The docs will document the existing behavior without changing runtime code. They will emphasize the project's safety-sensitive areas: Telegram session files, `.env` secrets, SQLite database files, per-chat cursor semantics, prompt-injection resistance, plain-text Telegram output, and the difference between manual preview digests and scheduled cursor-advancing digests.

## Developer Workflow

`docs/development.md` will make the local workflow explicit:

- Create and activate `venv`.
- Install `requirements.txt`.
- Copy `.env.example` to `.env`.
- Run `python main.py` after configuring credentials.
- Run tests with `venv/bin/python -m unittest discover -s tests`.

The workflow will call out that tests isolate imports and use fakes for Telegram, Gemini, and SQLite behavior.

## Future-Agent Workflow

`docs/agent-notes.md` and `GEMINI.md` will tell future agents to:

- Read `README.md`, `docs/index.md`, and `docs/agent-notes.md` first.
- Treat `.env`, `*.session*`, `*.db*`, and generated `.service` files as private local artifacts.
- Preserve cursor behavior: manual `/digest` must not advance cursors; scheduled sends advance only after all Telegram message parts send successfully; failed fetches or summaries must not advance affected chats.
- Keep Telegram responses plain text with `parse_mode=None` when sending user-controlled or AI-generated content.
- Run the unittest suite after behavior changes.

## Testing

Because this is documentation-only work, verification will focus on:

- Checking that all new documentation files exist and link to one another.
- Confirming the existing unittest suite still passes.
- Confirming the repo hygiene test continues to find the documented test command in `README.md` and `GEMINI.md`.

## Out Of Scope

This pass will not:

- Change bot behavior.
- Add new tests unless required by existing documentation-hygiene tests.
- Add diagrams, generated images, or browser-rendered assets.
- Introduce a documentation generator or static site framework.
