# Telegram Read-Only AI Assistant Docs

This directory is the deeper project guide for developers and future agents working on the Telegram Read-Only AI Assistant.

## Start Here

- [Development](development.md): local setup, test commands, and development workflow.
- [Architecture](architecture.md): Bot API front end, read-only Telethon gateway, local index, and assistant behavior.
- [Operations](operations.md): first-run auth, Bot API owner setup, systemd setup, private files, and troubleshooting.
- [Agent Notes](agent-notes.md): invariants and guardrails for future coding agents.

## Recommended Reading Order

1. Read the root [README](../README.md) for the user-facing quickstart.
2. Read [Development](development.md) before changing code.
3. Read [Architecture](architecture.md) before changing Bot API, Telethon, Gemini, SQLite, or retrieval behavior.
4. Read [Operations](operations.md) before changing deployment, service, or file-permission behavior.
5. Read [Agent Notes](agent-notes.md) before making automated or agentic changes.

## Generated Local Files

The assistant creates private runtime files locally. Do not commit or expose these files:

- `.env` and `.env.*` except `.env.example`
- `*.session*`
- `*.db*`
- `*.sqlite3*`
- `*.service`
- `*.log`

The repository `.gitignore` excludes these artifacts.
