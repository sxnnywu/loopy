# Setup — running the scoring engine (Modal)

The scoring runs on **Modal** (GPU cloud). The TRIBE weights, atlas, and the
precomputed demo scorecards are cached on a Modal **Volume** (`reeled-in-cache`)
that lives in **Jay's Modal workspace** (`jaychopra05`). So getting set up is two
parts: install + auth the CLI (each person, themselves), and get workspace access
(Jay grants it).

## ⚠️ Secrets are NOT in the repo — on purpose
This is a public repo. Modal tokens and API keys must never be committed (they'd
be exposed to the world). Each person authenticates themselves; shared service
keys are handed out privately or stored in Modal Secrets. Do not paste real keys
into any tracked file. `backend/.env` is gitignored; `backend/.env.example` lists
the names.

## 1. Install the Modal CLI (each person)
```
pip install modal          # or: python3 -m pip install --user modal
```

## 2. Authenticate (each person, themselves)
```
python3 -m modal setup      # opens a browser, approve — writes ~/.modal.toml
```
This creates YOUR own Modal token automatically (stored in `~/.modal.toml`, not
the repo). You do not need Jay's token.

## 3. ⚠️ Workspace access — ONLY JAY CAN DO THIS
Teammates can't see the cached weights/volume or run the functions until Jay adds
them to his Modal workspace:
- Jay: https://modal.com/settings/members → invite each teammate's email to the
  `jaychopra05` workspace.
- After accepting, run `python3 -m modal profile current` — it should show the
  shared workspace. Switch with `modal profile activate jaychopra05` if needed.

Without this step, `modal run` fails with a permissions/volume-not-found error.
This is the actual thing blocking the team.

## 4. Verify it works
```
python3 -m modal run backend/modal_app.py::smoke_test     # A100 boots
python3 -m modal run backend/modal_app.py::load_test      # TRIBE loads (uses cached weights)
```

## 5. Credentials the scoring lane needs
- **Modal auth** — from step 2 (per person). That's all the *scoring* functions need.
- **HF_TOKEN** — NOT required. We use the ungated `unsloth/Llama-3.2-3B` mirror, so
  there's no Meta gate to clear. (Optional: set your own for higher HF rate limits.)
- Other keys in `backend/.env.example` (`ELEVENLABS_API_KEY`, `MONGODB_URI`,
  `BACKBOARD_API_KEY`, `GEMINI_API_KEY`, `BACKEND_API_KEY`) belong to C's and D's
  lanes — get the shared values **from Jay directly**, put them in your local
  `backend/.env` (gitignored). For deployed functions, prefer a **Modal Secret**:
  `modal secret create reeled-in-secrets KEY=value ...` then reference it in the app.

## Notes
- First `load_test` per person is slow only if the volume cache is cold; it's
  warm already from Jay's runs, so it should be fast once you're in the workspace.
- Local Python version doesn't matter for the CLI (3.9+ fine); the GPU containers
  pin their own runtime.
