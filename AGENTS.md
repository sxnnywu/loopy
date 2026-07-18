# Rules for AI Coding Agents Working in This Repo

You are one of several coding agents working on this project in parallel, each driven by a different team member. These rules keep everyone's work compatible.

## 1. Read before you write

Before writing any code, read:

1. `SHARED_CONTRACTS.md` — every data shape, route, schema, and constant. Treat every code block in it as a specification to implement exactly.
2. `STATUS.md` — what is already done and what is currently in progress. Do not redo or overwrite in-progress work from another workstream.
3. The `PLAN.md` for the workstream you are operating in.

## 2. The contract is final

Once a field name, method signature, API path, collection name, or import path is committed in `SHARED_CONTRACTS.md`:

- Do NOT rename it
- Do NOT change its type
- Do NOT add required fields
- If a change is genuinely necessary, update `SHARED_CONTRACTS.md` first, mark the change clearly, and tell the human you are working with to announce it to the team before writing dependent code.

## 3. Stay in your workstream's lane

Each `workstreams/*/PLAN.md` lists what that workstream owns and does not own. Do not modify files owned by another workstream. If you need something from another workstream, code against the stub/contract and record the dependency in the "Handoff Notes" section of your PLAN.md.

## 4. Update the living docs — every session

Before ending a work session, you MUST:

- [ ] Check off completed items in the relevant `PLAN.md`
- [ ] Add new tasks discovered during the session to `PLAN.md` under "Next"
- [ ] Update `STATUS.md` (Done / In Progress / Next / Handoff Notes) with what changed
- [ ] Note any decisions or gotchas the next person/agent needs to know

This is not optional. The docs are how agents in different IDEs stay in sync. If context is compacted or a chat is cleared, these files are the only memory that survives.

## 5. Best practices

- Prefer official docs and READMEs of the open-source tools we use; read installation and usage guidance before integrating anything.
- Small, focused commits with clear messages describing what changed and why.
- No secrets in the repo. API keys live in `.env` (gitignored); document required env vars in `SHARED_CONTRACTS.md` §Env.
- Challenge weak ideas: if a task in a PLAN.md conflicts with the contracts or looks architecturally wrong, flag it to the human instead of silently implementing it.
