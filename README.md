# Chief — VYADA Systems Executive Console

AI Chief-of-Staff app built with Gradio + OpenAI. Tracks goals, tasks, projects,
clients, calendar, company OS (Rocks/Scorecard/Issues), and can now act on
natural-language requests via OpenAI function calling, not just slash commands.

## Project structure

- `app.py` — Gradio UI, slash-command routing, OpenAI function-calling loop, event wiring
- `video_gen.py` — optional fal.ai image-to-video integration
- `memory/store.py` — data layer: goals, tasks, rocks, scorecard, issues, decisions,
  workflows, clients, calendar, preferences, knowledge, plus the OpenAI client and
  department-agent orchestration (`run_team_task`)
- `nox_project_manager.py` — temporary stub; project-scanning commands are not implemented
- `memory_manager.py` — a `MemoryManager` class for JSON load/save (currently **not
  wired into the app** — `store.py` uses its own `mem_load`/`mem_save` functions with a
  `data/` directory. Keeping this here for a possible future refactor; see note below.)

## ⚠️ Known gap: `memory_manager.py` vs `store.py`

These are two different persistence approaches that currently coexist without being
reconciled:

| | `store.py`'s `mem_load`/`mem_save` | `memory_manager.py`'s `MemoryManager` |
|---|---|---|
| Storage dir | `data/` | `memory/` (default) — **conflicts** with `store.py`'s own migration, which moved data *out* of `memory/` since that's now a code package |
| Missing-file default | Caller-supplied (`[]` for lists, `{}` for dicts) | Always `{}` |
| Access pattern | Key → filename via `MEMORY_FILES` dict | Direct filename |

**Do not swap `MemoryManager` in for `mem_load`/`mem_save` as-is** — using its default
`memory/` directory would write data back into the code package, and its `{}` default
would break every `store.py` function that expects a list back (`.append()` calls would
fail on first use). If/when this gets reconciled, `MemoryManager` needs its default
directory changed to `data/` and a caller-supplied default value, at minimum.

## Setup

```bash
pip install -r requirements.txt
```

Create a `.env` file (never commit this):
```
OPENAI_API_KEY=sk-...
TELEGRAM_BOT_TOKEN=...   # optional, for morning briefing push
TELEGRAM_CHAT_ID=...     # optional
FAL_KEY=...              # optional, for video generation
```

## Running

```bash
python app.py
```

Opens at `http://127.0.0.1:7860`.

## Known limitations

- `nox_project_manager.py` is a stub so the app can import; `/continue`, `/lock`, and
  `/link-project` are unavailable until the real project manager is implemented.
- Natural-language function calling covers the most common actions (tasks, goals,
  rocks, scorecard, issues, clients, calendar, preferences, knowledge, workflows,
  decisions, team consultation, web search) — see `TOOLS` in `app.py`. It does not
  yet cover the `nox_project_manager.py`-backed commands (`/continue`, `/lock`,
  `/link-project`).
