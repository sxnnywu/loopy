# Platform Research — Backboard.io

**Role in Loopy (Layer 2 — Loopy's QA infrastructure):** the **memory + routing layer for Loopy's Analysis Engine**. Two jobs: (1) **longitudinal QA memory scoped per `spec_id`** so Loopy remembers what it learned about a loop across every batch (trends, regressions, recurring-vs-new findings), and (2) the **stateful router** that serves Loopy's analysis model (Gemini among others).

> Layering note: Backboard is *Loopy's* infra here. It also appears *inside* the demo morning-triage loop as that loop's memory — but that's the **Layer-1 demo loop's choice**, swappable, not a Loopy requirement. This doc is about the Layer-2 use.

---

## Product overview (2026 state)
Backboard is "one API, 17,000+ LLMs, persistent memory." Two things make it more than an LLM proxy:

**1. Production-grade memory.** It extracts, organizes, and retrieves relevant facts from interactions and **attaches memory to entities** (users, teams, *workflows* — or, for us, a *loop under test*) rather than to a single session. Retrieval is **LLM-guided semantic**, not raw vector similarity. Two tiers: **Memory Lite** (fast recall) and **Memory Pro** (deep multi-hop). Tops memory benchmarks (90.1% LoCoMo, 93.4% LongMemEval).

**2. Stateful model router.** One unified API in front of 17,000+ models (OpenAI, Anthropic, Gemini, open-source); memory is portable across models; RAG + web search + embeddings live in the same API.

## Latest 2026 features
Unified API (context+memory in one call), Voice API (STT/TTS incl. ElevenLabs), Image gen tool, Multimodal RAG, Web Search Mode, Memory v0.4, TypeScript SDK, OpenRouter BYOK, AWS Bedrock.

## How Loopy uses it (Layer 2) — "above and beyond"
1. **Longitudinal QA memory scoped to `spec_id`.** Attach a Backboard memory entity to *each registered loop*. Every batch's findings are written to that memory, so the next time you QA the same loop Loopy recalls the last results and reports **regressions/trends** — "nod rate 9% → 6% → 4% across your last three runs," "this stall cluster is recurring," "this is a *new* failure since last week." This turns Loopy from a one-shot report into a **QA history**, which is a genuine product upgrade, not a sponsor bolt-on.
2. **Analysis Engine routing.** Loopy's findings step calls its reasoning model *through* Backboard's stateful router — so the analysis model is unified/swappable (Gemini today, anything tomorrow) and the analysis agent carries memory of prior findings so it doesn't re-report known issues.
3. **"Seen this before?" recall.** Backboard's semantic memory/RAG answers whether a failure signature has appeared before — within this loop, and (stretch) across loops — complementing Mongo's *within-batch* vector clustering with *cross-batch* recall.

**Division of labor (no redundancy):** MongoDB = event store + within-batch stats + within-batch failure clustering. Backboard = cross-batch longitudinal memory + analysis routing. Gemini = the reasoning model (served via Backboard).

## Why Backboard, and why this way
Chosen because Loopy needs **memory that persists across QA runs** (entity-scoped, LLM-agnostic) and a **router** to serve its analysis model — both first-class Backboard primitives. Using it as Loopy's longitudinal-memory + routing layer (not as a generic model gateway) makes it load-bearing in our infrastructure and unlocks trend/regression reporting. Cash-prize track ($200 + up to $1,000 credits + VC intros).

## Sources
- [Backboard — memory](https://backboard.io/products/memory) · [Stateful routing](https://backboard.io/products/stateful-routing) · [Changelog](https://backboard.io/changelog) · [SDK quickstart](https://docs.backboard.io/sdk/quickstart)
