# 🎣 Reeled In

**Neural A/B testing for short-form video. Know which edit hooks the brain before you post.**

> Hack the 6ix 2026 · Toronto · Jul 17–19

## What it does

Upload two or more versions of a Reel or TikTok. Or give a voiceover script and we generate voice versions for you. Reeled In predicts how the brain reacts to each one using Meta's open-source **TRIBE v2** brain model. It breaks the predicted brain response into **5 systems** (visual, auditory, language, motion, default-mode), measures engagement over time, and picks a winner. All before you post, in seconds, no focus groups.

The name: Instagram **Reel** plus "**reeling you in**." The metric is whether the content hooks and holds the viewer's brain.

## Why

Short-form video has too many creative choices (hook, music, cut order, pacing, captions, CTA) and no cheap way to test them before posting. Creators guess, then find out after posting or after spending on ads. The only real testing today is posting live or paying for focus groups.

We predict brain activation, not sales or virality. It is a fast directional read, not ground truth. We say that up front.

## MVP scope

Two test types:

1. **Upload and compare.** Upload 2+ finished versions. We score and compare. No auto video editing.
2. **Voice A/B.** Upload one base video plus a script. We generate several voice reads with ElevenLabs, overlay each on the video, and score them.

**Winner:** for each version we compute peak engagement, sustained engagement, and how well it holds attention to the end. You pick the goal. Highest score on that goal wins.

## Architecture

```
[Creator's browser]
      |  upload versions / voice script
      v
[Base44 frontend]  --login-->  Auth0
      |  authenticated request
      v
[FastAPI on Modal]  (Python backend / orchestrator)
   |-> Modal GPU: TRIBE v2 scoring (or precomputed)
   |-> ElevenLabs: voice generation (Voice A/B)
   |-> Backboard: suggestions + memory
   |-> MongoDB Atlas: store tests/scores
      |  results JSON
      v
[Base44 frontend]  shows winner + brain curves
```

| Piece | Role |
|---|---|
| **Base44** | Frontend: upload, results screen |
| **Auth0** | Login |
| **FastAPI on Modal** | Python backend. All logic, secrets, orchestration |
| **Modal GPU** | Runs TRIBE v2 on an A100. Demo scores precomputed |
| **MongoDB Atlas** | Stores tests, versions, scores, users |
| **Backboard** | Suggestions and memory |
| **ElevenLabs** | Voice generation for Voice A/B |

Two backends by design. Base44 can't run heavy ML or reliably reach Atlas. Python isn't a good frontend with login. So secrets and heavy work live in Python, and Base44 is the front door.

## Setup

Scoring runs on Modal. See [`SETUP.md`](SETUP.md) to install the CLI, log in, and get workspace access. Short version: `pip install modal`, then `python3 -m modal setup`, then Jay adds you to the Modal workspace.

## Team (4 lanes)

Everyone builds against mocks off two frozen contracts (the API and the Score Object) so no one blocks anyone. Detail in [`TEAM_DIVISION.md`](TEAM_DIVISION.md).

| Lane | Owns |
|---|---|
| **A. Frontend** (Base44) | The whole app: upload, results screen, brain visual, login, design |
| **B. Scoring** (TRIBE on Modal) | TRIBE scoring, 5 brain systems, metrics, Score Object, brain frames, demo scores. Plus objective signals (motion, blur, clarity, speech, face, hands) |
| **C. Backend** (FastAPI + Mongo) | All endpoints, Mongo, auth, serving media, orchestration |
| **D. Generation** (ElevenLabs + Backboard) | Voice A/B pipeline, Backboard memory, Gemini suggestions, demo clips |

```
A (UI)       -> calls -> C (API)
C (API)      -> calls -> B (score) and D (generate)
D (versions) -> feeds -> B (to score)
B (scores)   -> stored -> C (Mongo)
```

Build plan and per-file owners: [`PARALLEL_IMPLEMENTATION_PLAN.md`](PARALLEL_IMPLEMENTATION_PLAN.md).

## Docs

- [`SETUP.md`](SETUP.md): install and run the scoring engine
- [`OVERVIEW.md`](OVERVIEW.md): scope, prize tracks, logistics
- [`TEAM_DIVISION.md`](TEAM_DIVISION.md): the 4 lanes and contracts
- [`PARALLEL_IMPLEMENTATION_PLAN.md`](PARALLEL_IMPLEMENTATION_PLAN.md): phases, repo layout, dependencies
- [`CONTRACTS.md`](CONTRACTS.md): the data shapes every lane shares
- [`PRD.md`](PRD.md): users, features, metrics, risks
- [`TECH_ARCHITECTURE.md`](TECH_ARCHITECTURE.md): full system design
- [`HOW_TRIBE_V2_WORKS.md`](HOW_TRIBE_V2_WORKS.md): the brain model, the 5 systems, limits
- [`PERSON_B_SCORING.md`](PERSON_B_SCORING.md): scoring engine hand-off
- [`NORMALIZATION_DECISION.md`](NORMALIZATION_DECISION.md): why per-clip normalization was left as-is
- [`evals/`](evals/): validation runs

## Honest limits

- Brain activation is not the same as sales. It is an engagement proxy.
- The brain model is slow (about 1 reading per second), so it is reliable at the few-second level, not frame by frame.
- It was trained on long real-world video, so short punchy Reels are directional.
- TRIBE is licensed CC BY-NC. Fine for the demo, not for a paid product. We validate with a free beta.

## Prize tracks

- **Base44**: the app is built on it. Validated with a free beta.
- **ElevenLabs**: powers Voice A/B.
- **MongoDB Atlas**: stores everything.
- **Backboard**: suggestions and memory.
- **Gemini** (MLH): direct call for suggestions.
- **Auth0** (MLH): login.
- Out: Phoebe.

## Hackathon

36 hour build. First Devpost by 11:59 PM Sat. Live 5-minute pitch, public repo, demo video. Judged on Technical Difficulty, Uniqueness, Design, Completeness. The TRIBE scoring pipeline is our technical core. The judges penalize plain API wrappers, and our real work is the brain-system reduction, the metrics, the winner logic, and the visual.
