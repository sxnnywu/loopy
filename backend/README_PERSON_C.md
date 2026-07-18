# Person C — Analysis — plain-language guide

You own the part of Loopy that turns **raw run data into the QA findings**. You're
the "so what does it all mean" brain. Everyone else moves data around; you're the
one who says *"36% of runs stalled, and here's the exact handoff that caused it."*

## What your code does, in order
1. **Read** the run data other people's code put in MongoDB (two collections:
   `sandbox_runs` = one row per test run, `events` = every message the agents sent).
2. **Do the math** (`app/services/analysis/pipelines.py`): completion rate, stall
   rate, iteration spread, token cost, divergence, per-handoff fragility.
3. **Cluster the failures + write findings** (next step: `clustering.py` + Gemini).
4. **Assemble the report** (next step: `report_builder.py`) and serve it at
   `GET /api/runs/{run_id}/report` (`routes/reports.py`).

Rule you must never break: **math decides, the LLM only narrates.** The numbers
come from Mongo pipelines. Gemini only writes the English sentence around them.

## The trick that means you're NOT blocked
You'd normally have to wait for Person A (who generates the runs) and Person B (who
stores them). Instead you have your **own fake data generator**
(`scripts/seed_fake_run.py`). It fills Mongo with realistic, contract-shaped data —
including a planted "multi-currency stall" failure — so you can build and test 100%
of your analysis today, alone. When A & B are ready, you delete nothing: their real
data has the exact same shape, so your pipelines just work on it.

## Run it yourself (from this `backend/` folder)
```bash
# one-time: start a local Mongo + install deps
docker run -d --name loopy-mongo -p 27017:27017 mongo:7
./.venv/bin/pip install pydantic pymongo

# every time you want fresh data + stats:
./.venv/bin/python -m scripts.seed_fake_run       # fill Mongo with fake runs
./.venv/bin/python -m scripts.run_analysis_demo   # print all your stats
```
Stop Mongo when done: `docker rm -f loopy-mongo` (data is disposable).

## What you're waiting on someone else for (small stuff)
- **B's `core/database.py`** — the real Mongo connection. You use a local one for now;
  swap the import when B's lands. Same collection names (locked in the contract).
- **A's shared models module** — you have a mirror in `app/models.py`. Reconcile the
  import path when A commits the canonical one.
- **A's convention for "control pairs"** (which runs share a seed) — needed for the
  divergence metric to be exact. You assume "equal `seed_input` = same group" for now.
- **Gemini API key + confirmed model IDs** — needed only for the findings-narration
  step, not for any of the math above.
