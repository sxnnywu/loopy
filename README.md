# Loopy — QA for Loop-Engineered Agent Systems

Loopy is a QA and observability platform for loop-engineered agent orchestration systems. It stress-tests agent loops by spinning up large fleets of isolated sandboxes (target: 1,000+), capturing every agent-to-agent interaction, and turning that raw data into actionable QA findings.

## Read Order

If you are a human or a coding agent picking this project up for the first time, read in this order:

1. `DUMMY_EXPLANATION.md` — plain-language version of what this is
2. `PROJECT_OVERVIEW.md` — problem, thesis, solution phases
3. `INTEGRATIONS_AND_STACK.md` — priority integrations vs nice-to-have, full stack
4. `ARCHITECTURE_FLOW.md` — how the system fits together end to end
5. `SHARED_CONTRACTS.md` — **single source of truth** for data shapes, routes, schemas
6. `TEAM_DIVISION.md` — workstreams, ownership, contract-first rules
7. `EXAMPLE_RUN_FLOW.md` — walkthrough of one full QA run
8. `STATUS.md` — living doc: what is done, in progress, and next
9. `workstreams/*/PLAN.md` — per-workstream execution plans

## Source-of-Truth Precedence

When documents disagree:

`SHARED_CONTRACTS.md` > `TEAM_DIVISION.md` > `ARCHITECTURE_FLOW.md` > everything else

## Living Documents Rule

Every doc in this repo is a living document. Any time work is completed, started, or re-scoped:

- Update the checkboxes in the relevant `workstreams/*/PLAN.md`
- Update `STATUS.md` (Done / In Progress / Next / Handoff Notes)
- If a data shape, route, or import path changed: update `SHARED_CONTRACTS.md` FIRST and announce it to the whole team

Stale docs are treated as bugs.

## For AI Coding Agents

See `AGENTS.md` at the repo root. It defines the rules you must follow before writing any code in this repo.
