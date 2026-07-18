# Interface & Design Workstream — Execution Plan

Source of truth priority: `SHARED_CONTRACTS.md` > `TEAM_DIVISION.md` > `ARCHITECTURE_FLOW.md`.

This workstream is owned by the team's presenter/designer. Technical members support on API wiring; the owner focuses on design, communication, and the demo. This split is intentional — see `TEAM_DIVISION.md`.

Non-negotiable contract rules:
- Frontend types mirror `SHARED_CONTRACTS.md` §3 exactly (same field names)
- It is `run_id` everywhere
- Do not code against routes that aren't in contracts §5

## Scope

You own:
- Dashboard (Base44 primary candidate — confirm): fleet status view, live traffic feed, report viewer
- Visual design following our existing design templates (do not invent a new visual system)
- Partner/stakeholder communication during the event
- Demo script + presentation deck
- Nice-to-have: Eleven Labs voice narration of the report

You do not own:
- Backend logic, schemas, orchestration

## Deliverables

- [ ] Fleet view: state counts + grid of sandbox states, live
- [ ] Traffic feed: sampled `agent_message` events streaming, readable
- [ ] Report view: summary, findings (severity-coded), stats charts
- [ ] Spec registration form (simple; can be JSON paste for MVP)
- [ ] Demo script (the "one anecdote vs a distribution" narrative in EXAMPLE_RUN_FLOW.md)
- [ ] Presentation deck on our templates

## Step-by-Step

### Step 1 (parallel with backend stubs)
- [ ] Confirm Base44 fit; log decision in INTEGRATIONS_AND_STACK.md
- [ ] Apply design templates: palette, type, layout shells
- [ ] Mock all three views against contract shapes with fake data

### Step 2 (wiring — with a technical member)
- [ ] Typed API client mirroring contracts §5
- [ ] WebSocket hookup for fleet + traffic
- [ ] Swap fake data for real

### Step 3 (narrative)
- [ ] Demo script drafted + rehearsed end to end twice
- [ ] Talking points per integration (why each is in the architecture)
- [ ] Nice-to-have: Eleven Labs narration of report summary

## Confirm with Data & Storage
- [ ] WebSocket message shapes
- [ ] Report JSON final before report view

## Confirm with Orchestration
- [ ] Fleet state counts shape

## Risks
- [ ] Do not block on live data — build everything against fake contract-shaped data first
- [ ] Do not restyle mid-build; templates are final
- [ ] Demo depends on ONE rehearsed happy path plus ONE rehearsed failure-finding moment — protect those

## Success Criteria
- [ ] Dashboard shows a live run, renders a real report, and the demo is rehearsed

---

## Living Status (update every session)

**Done:** —
**In progress:** —
**Next:** Step 1
**Handoff notes:** —
