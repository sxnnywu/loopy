# Platform Research — Gemini API

**Role in Loopy (Layer 2 — Loopy's QA infrastructure):** the **reasoning model behind Loopy's Analysis Engine** — the model that reads clustered failures and writes the human-readable `Finding`s. It is served *through Backboard's router*.

> Layering note: Gemini is *Loopy's* analysis brain here. It also powers the agents *inside* the demo morning-triage loop — but that's the **Layer-1 demo loop's choice** (a user's real loop could run any model; Loopy is model-agnostic about the loop it tests). This doc is about the Layer-2 use.

---

## Product overview (2026 state)
The Gemini 3.x generation is current. Tiers relevant to us:
- **Gemini 3.5 Flash** (GA) — flagship for agentic/coding tasks; 1M context, 65k output. **Our analysis/findings model.**
- **Gemini 3.1 Flash-Lite** — cost-optimized, high-volume (used by the *demo loop's* triage agent — Layer 1).
- Gemini 3 Flash Preview — legacy fallback.

## Latest features worth using (and why)
- **`thinking_level` enum** (`minimal|low|medium|high`) — reasoning depth = cost/latency control. Use `high` for the findings pass.
- **Structured outputs (JSON mode / response schema)** — force JSON matching the `Finding` schema → zero parsing.
- **Batch API** — cheaper async bulk jobs; our analysis pass is batchable.
- **Context caching** — cache a reused prompt prefix; pay for it once.
- **Automatic thought preservation**, tool integration (Search grounding, URL context, code exec, functions), Computer Use (preview).
- **3.x migration:** remove `temperature`/`top_p`/`top_k` — 3.x is tuned for defaults.

## How Loopy uses it (Layer 2) — "above and beyond"
1. **Structured output for `Finding`s.** The analysis step calls Gemini with a response schema mirroring the `Finding` Pydantic model (`severity`, `title`, `description`, `evidence_sandbox_ids`, `stat`) — guaranteed shape, so `report_builder` just validates and stores.
2. **Batch API for the analysis pass.** Summarizing thousands of failure transcripts per batch is inherently batchable → one Batch job, large cost cut vs sequential calls.
3. **Context caching on the shared analysis prompt.** The findings prompt/rubric is reused across every cluster in a batch → cache it once.
4. **`thinking_level: high` on findings only.** We want depth on the one analytical step; we don't pay for it elsewhere.
5. **Served via Backboard's router** — so the analysis model is swappable and the analysis agent carries memory of prior findings (see `research/backboard.md`).
6. **Restraint:** we do *not* bolt on Search grounding — the analysis is over our own event data. Knowing when *not* to use a feature is part of using the tool well.

**Division of labor:** Mongo computes the numbers; Python does the sequence/oracle logic; **Gemini writes the sentences** (the findings narration). Math decides, the LLM narrates.

## Why Gemini, and why this way
Chosen for structured output + Batch + caching (reliable, cheap analysis at fan-out scale) and tier flexibility. It's Loopy's Layer-2 reasoning model, not something we impose on the loop under test. MLH track (Best Use of Gemini).

## Sources
- [Gemini API changelog](https://ai.google.dev/gemini-api/docs/changelog) · [What's new in 3.5 Flash](https://ai.google.dev/gemini-api/docs/whats-new-gemini-3.5) · [Models](https://ai.google.dev/gemini-api/docs/models) · [Gemini 3 guide](https://ai.google.dev/gemini-api/docs/gemini-3)
