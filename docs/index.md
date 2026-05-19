# Telegram Digest Bot Docs

This directory is the deeper project guide for developers and future agents working on the Telegram Digest Bot.

## Start Here

- [Development](development.md): local setup, test commands, and development workflow.
- [Architecture](architecture.md): how the bot collects messages, summarizes them, stores cursors, and sends digests.
- [Operations](operations.md): first-run auth, systemd setup, generated private files, scheduling, and troubleshooting.
- [Agent Notes](agent-notes.md): invariants and guardrails for future coding agents.

## Recommended Reading Order

1. Read the root [README](../README.md) for the user-facing quickstart.
2. Read [Development](development.md) before changing code.
3. Read [Architecture](architecture.md) before changing digest, cursor, Telegram, Gemini, or database behavior.
4. Read [Operations](operations.md) before changing deployment, service, or file-permission behavior.
5. Read [Agent Notes](agent-notes.md) before making automated or agentic changes.

## Generated Local Files

The bot creates private runtime files locally. Do not commit or expose these files:

- `.env` and `.env.*` except `.env.example`
- `*.session*`
- `*.db*`
- `*.sqlite3*`
- `*.service`
- `*.log`

The repository `.gitignore` excludes these artifacts.
