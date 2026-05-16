# Contributing

Thanks for considering a contribution. This repo is designed for **experimentation**: drop your trading algorithm onto its own branch, compare it against the baseline, and either keep it as a personal fork or open a PR back to `main`.

---

## Branching model

Keep `main` clean and reviewable. Use prefixes:

| Prefix | Purpose | Example |
|---|---|---|
| `strategy/<name>` | A new trading algorithm | `strategy/rsi-divergence` |
| `feature/<name>` | New product feature (UI, API, ingestion source) | `feature/options-data` |
| `fix/<name>` | Bug fix | `fix/scheduler-job-overlap` |
| `docs/<name>` | Docs-only changes | `docs/glossary` |
| `chore/<name>` | Build, deps, config, tooling | `chore/upgrade-fastapi` |

One concern per branch — do not bundle a strategy with a UI redesign.

## Drop-a-strategy workflow

The pluggable strategy interface is the next milestone (see [`docs/STRATEGIES.md`](docs/STRATEGIES.md)). High-level steps once it lands:

1. Fork the repo, then branch: `git checkout -b strategy/<your-name>`
2. Create `backend/app/strategies/<your_strategy>.py` — subclass `BaseStrategy`, implement `generate_signal()` and `generate_entries_exits()`, decorate with `@register_strategy`
3. Register it for import in `backend/app/strategies/__init__.py`
4. Run the parity + round-trip tests:
   ```bash
   PYTHONPATH=backend uv --project backend run pytest tests/test_strategies.py -v
   ```
5. Run a backtest against the baseline:
   ```bash
   curl -X POST http://localhost:8000/api/backtest \
     -H 'Content-Type: application/json' \
     -d '{"symbol": "AAPL", "interval": "1d", "strategy_name": "<your_name>"}'
   ```
6. Open `/backtest/compare` in the dashboard and overlay your strategy's equity curve against `baseline`
7. (Optional) Open a PR — or just keep it on your fork

For Claude Code users: invoke the `strategy-validator` subagent (`.claude/agents/strategy-validator.md`) on your strategy file. It runs the parity test and reports PASS/FAIL.

## Commit convention

[Conventional Commits](https://www.conventionalcommits.org/). Examples from this repo's history:

```
feat: add LLM advisory, chart analysis, chat, and indicator overlays
fix(ux): align frontend API shapes with actual backend responses
docs: add comprehensive CLAUDE.md documentation across all domains
chore: bump pandas-ta-classic
```

Keep the subject under 72 characters. Use the body for the "why" when it isn't obvious from the diff.

## Testing

Before opening a PR:

```bash
# Backend unit + integration tests
PYTHONPATH=backend uv --project backend run pytest tests/ -q

# Frontend lint
cd frontend && npm run lint

# Frontend E2E (Playwright — backend + frontend must be running)
cd frontend && npx playwright test
```

If you add new analysis logic, write a pure-function test in `backend/tests/` first — no DB, no FastAPI, no scheduler. The existing `test_indicators.py`, `test_signals.py`, and `test_backtest.py` are the templates.

## Database migrations

Schema changes go through Alembic:

```bash
cd backend
uv run alembic revision -m "<short description>"
# Edit the new file under alembic/versions/
uv run alembic upgrade head    # apply locally
uv run alembic downgrade -1    # verify rollback works
```

Always implement `downgrade()`. Never edit a migration that has been merged to `main`.

## Pre-PR checklist

- [ ] Branch named with the right prefix
- [ ] All backend tests pass (`pytest tests/ -q`)
- [ ] Frontend lint passes (`npm run lint`)
- [ ] Any new migration has both `upgrade()` and `downgrade()`, verified locally
- [ ] No `.env` or secrets staged (`git status` is clean of those paths)
- [ ] `CLAUDE.md` updated if you changed module structure, conventions, or added a new pattern
- [ ] Commit messages follow Conventional Commits

## Claude Code workflow

You don't need Claude Code to contribute, but if you use it:

- Six `CLAUDE.md` files (root + 5 sub-domain) load context automatically. No `/init` needed.
- The project ships a `strategy-validator` subagent in `.claude/agents/` — use it to validate a new strategy before pushing.
- The GSD workflow (`get-shit-done/`) is the original planning system used to build this. Optional for contributors.

## Code of conduct

Be respectful. Disagree on technical merit, not personal attacks. Trading is opinionated — we expect disagreements about indicators, weights, and strategies. Keep it about the math.

## Reporting security issues

Please **do not** open a public issue for security vulnerabilities (credential leaks, auth bypass, injection). Open a private security advisory on GitHub instead, or contact the maintainer through their GitHub profile.

## License

By contributing, you agree your contributions will be licensed under the [MIT License](LICENSE).
