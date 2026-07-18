# Person C — Backend & Data — Plan (Reeled In)

**Owner:** Person C (Backend & Data — FastAPI on Modal + MongoDB Atlas).
**Last updated:** 2026-07-18.
**Reconciled against:** Person A's frontend contract (`frontend/mock_api.json`), `CONTRACTS.md` (law), `TEAM_DIVISION.md` Lane C, `PARALLEL_IMPLEMENTATION_PLAN.md`.

> This plan supersedes the Lane-C bullets scattered in `TEAM_DIVISION.md` / `PARALLEL_IMPLEMENTATION_PLAN.md` by pulling them into one owner doc, reconciling them with what Person A actually consumes, folding in a MongoDB "above-and-beyond" feature layer, and listing every cross-lane misalignment found in the codebase audit (§3). It changes **no** field/route names — where the code and `CONTRACTS.md` disagree, that's logged in §3/§8 as a contract-change request to raise with the team, not a unilateral rename.

---

## 1. C's scope (unchanged from TEAM_DIVISION Lane C)

C is the **integration hub**: the FastAPI app on Modal (all `/api` routes), the MongoDB Atlas schema + persistence, auth verification, media storage/serving, and the orchestration that calls **B**'s scorer and **D**'s generators. C owns everything in `backend/` except `scoring/` (B) and `generation/` (D).

C does **not** own: model internals (B), voice/LLM internals (D), or any UI (A). C's interface to the rest of the team is the REST contract in `CONTRACTS.md §5` — that is the seam with A, and calling B/D as functions is the seam with them.

---

## 2. How C connects to Person A (the reconciliation)

Person A builds the entire Base44 app against `frontend/mock_api.json` and swaps in C's real endpoints at Phase 3. **A never adapts to C — C must serialize byte-for-byte what the mock promises.** Concretely, A depends on C for all of the following, and each is a C deliverable:

| What A consumes | Exact shape A expects | C must deliver |
|---|---|---|
| `GET /api/tests/{test_id}` | `{ test, variants, scores }` — top-level keys exactly as `mock_api.json` | `TestDetail` (schemas.py) — already matches ✅ |
| Test object PK | `test.id` (mock uses `id`, **not** `test_id`) | Serialize the Test's own id as `id` — see the `id`/`test_id` conflict in §3 (#2) |
| Variant object | `variants[].id`, `.test_id`, `.label`, `.media_key`, `.params`, `.created_at` | matches ✅ |
| Score Object | Full §3 shape incl. `engagement`, `brain_frames`, `region_timeline` | C must **store and return all three** — the §4 `scores` doc sketch omits them (§3 #6) |
| Scoring status | `POST /score` returns fast; A **polls `GET /tests/{id}` every ~1.5 s** until `status ∈ {complete, failed}` | C implements the async status transitions (`pending→scoring→complete/failed`) |
| History list | `GET /api/history → { tests: [TestSummary] }` — lightweight, with `variant_count` + `winner{variant_id,label}` | C must add a `TestSummary` model — it does not exist yet (§3 #1) |
| Auth | A attaches `Authorization: Bearer <auth0_jwt>` (client-side Auth0 SPA SDK; Base44 app is Public) | C verifies the JWT against Auth0 JWKS + upserts `users` (§3 #4) |
| Cross-origin calls | A's browser calls C directly from `https://<app>.base44.app` | **C must enable CORS for `ALLOWED_ORIGINS`** — currently absent (§3 #5) |
| Media (video + brain PNGs) | A renders `media_key` values (`.mp4` playback, `_brain_###.png` flipbook) | **C must expose a way to fetch bytes for a `media_key`** — no such route exists (§3 #7) |
| Explanations | `POST /explain → { explanations: { "<variant_id>": [{t,text}] } }` | C orchestrates D's `explainer.explain()` per variant into that dict |

**The two reconciliation items A is most silently blocked on** (neither is in the contract yet, both are C-owned): **CORS** and a **media-serving route**. Without CORS, every real A→C call fails in the browser the moment A stops using the mock. Without a media route, A has `media_key` strings but no URL to load the video or the brain-frame PNGs. Both are raised as contract changes in §8.

---

## 3. Cross-lane alignment audit (full codebase review)

Reviewed every file in `backend/`, `frontend/mock_api.json`, and `CONTRACTS.md`. Findings, most-actionable first. "Owner" = who fixes it.

| # | Finding | Where | Sev | Owner |
|---|---|---|---|---|
| 1 | **`/history` returns the wrong shape.** `schemas.py:HistoryResp = {tests: list[Test]}`, but `CONTRACTS §5` requires `{tests: [TestSummary]}` (lightweight: `test_id, type, objective, status, created_at, variant_count, winner{variant_id,label}`). No `TestSummary` model exists. | `backend/models/schemas.py:75` | High | **C** |
| 2 | **Test/Variant PK key conflicts with §1.** `CONTRACTS §1` says the identifier is `test_id` "everywhere — never `id`", but the `Test`/`Variant` wire objects (schemas.py **and** `mock_api.json`) serialize their own PK as `id`. A and C already agree on `id`; the *rule text* is what's out of sync. Needs a one-line contract clarification (PK = `id`; `test_id` is the foreign-key / TestSummary name) so nobody "fixes" it unilaterally and breaks A. | `schemas.py:46,54` · `mock_api.json:3,18` · `CONTRACTS §1` | High | **C** raises; team ratifies |
| 3 | **`.env.example` is stale vs `CONTRACTS §8`.** Still lists removed `BACKEND_API_KEY`; missing `ALLOWED_ORIGINS`, `AUTH0_DOMAIN`, `AUTH0_AUDIENCE`. (Fixed in this pass — see §10.) | `backend/.env.example` | Med | **C** ✅ |
| 4 | **No auth anywhere.** `CONTRACTS §6` specifies Auth0-JWT-via-JWKS verification → `user_id`, but every route is an unauthenticated stub and there's no JWKS/verify code. | `backend/api/*`, `backend/main.py` | High | **C** |
| 5 | **No CORS.** Free-plan model has the browser calling C cross-origin; `main.py` has no `CORSMiddleware`. Real A→C calls will fail in-browser. | `backend/main.py` | High | **C** |
| 6 | **Stored score would drop fields A needs.** `CONTRACTS §4`'s `scores` doc sketch lists only `networks, metrics, duration_sec, sample_rate_hz` — but B's `score()` and §3 also produce `engagement`, `brain_frames`, `region_timeline`. If C persists only the §4 fields, A loses the composite curve + brain animation. C must store the **full** Score Object. | `CONTRACTS §4` vs `scoring/score.py` | High | **C** (+ doc fix) |
| 7 | **No media-serving route.** `media_key` is defined (§7) but there is no `GET` endpoint (or signed-URL scheme) to fetch the bytes. A cannot display video or brain PNGs. | `CONTRACTS §5` | High | **C** raises + builds |
| 8 | **Sync pymongo under async FastAPI.** `db/mongo.py` uses `MongoClient` (blocking). Motor is deprecated (EOL May 2026); the current recommendation is **PyMongo Async (`AsyncMongoClient`)**. Sync calls block the event loop and, on Modal, the lazy global needs per-container lifecycle + tuned pool. | `backend/db/mongo.py` | Med | **C** |
| 9 | **`requirements.txt` gaps for C's own work.** Add `pyjwt[crypto]>=2.10.1` (RS256 + `PyJWKClient`; pins clear of PyJWT CVEs), pin `pymongo>=4.9` (AsyncMongoClient), `fastapi[standard]>=0.115` + `python-multipart>=0.0.9` (uploads), and `voyageai` only if adding vector search (§5). Do **not** add `python-jose`. | `backend/requirements.txt` | Med | **C** |
| 10 | **Demo data is undifferentiated.** `mock_api.json`'s two variants are byte-identical with `retention=1.0`, so the winner (`var_demoB`) isn't derivable from the scores. Fine for A's shape-dev, but the **seeded** demo (`seed_demo.py` + D's dataset) must have distinct curves so the live winner reveal is real. | `mock_api.json`, `db/seed_demo.py` | Low | **C**+**D** |
| 12 | **Media location mismatch (D writes ≠ B reads).** **All** of D's file I/O — `overlay.py`, `voice.py`, `gemini.py` (reads the base video for /suggest), and `llm.py` (thread-map JSON) — resolves under **repo-root** (`parents[2]/media`); B's `score.py` resolves under the **Modal Volume** (`/cache/media`). On Modal these are different containers, so a generated variant / uploaded base video is invisible to the GPU scorer and to Gemini. The contract (§7) makes media **C's concern** but never pins the physical root. C must define **one** `MEDIA_ROOT` (the Volume `/cache/media`) that B and D both resolve against — inject it (env/param) or copy files onto the Volume. | `generation/*.py` vs `scoring/score.py:16` | High | **C** (coord B+D) |
| 13 | **`api()` doesn't mount the media Volume.** `modal_app.py` mounts the `cache` Volume on `score_gpu` but **not** on the `api()` ASGI function → C cannot persist uploads to, or serve media from, the shared Volume. Add `volumes={CACHE_DIR: cache}` to `api()` (and `commit()`/`reload()` for cross-container read-after-write). | `backend/modal_app.py:42` | High | **C** |
| 11 | **Consistent, no action:** D's `generate_voice_variants` returns `test_id: None` ("C assigns on persist") ✅; B's `score()` returns `brain_frames: []` in Phase 1 (contract allows empty) ✅; `TestDetail` matches `mock_api.json` ✅; metric formulas in `scoring/metrics.py` match `CONTRACTS §3` ✅; `mock_variants.py` now mirrors the VoiceSpec `params` echo ✅. | — | — | — |

**Net:** B and D are on-contract at the **data** level (shapes, fields, formulas all match). The gaps are all in **C's** integration surface — the API/auth/CORS layer and, newly, the **Modal media wiring** (#12/#13): the physical media root and Volume mounts that no lane currently owns end-to-end. C closes them; the plan below sequences it.

---

## 4. C's build plan by phase

Phases mirror `PARALLEL_IMPLEMENTATION_PLAN.md`. ✅ = done, ▶ = do now, ○ = later.

### Phase 0 — Scaffold & contracts (done / in progress)
- ✅ Repo skeleton, `main.py`, `modal_app.py`, `schemas.py`, route stubs, `mongo.py`.
- ▶ Raise the §8 contract changes (CORS, media route, `id`/`test_id` clarification, full-Score-Object storage) so A/B/D ratify before integration.
- ▶ Provision Atlas cluster (M0 is fine — vector search + search indexes work on M0); put `MONGODB_URI` in the Modal secret store; cluster region = Modal region.

### Phase 1 — API on stubs (max parallelism; C unblved by nobody but contracts)
- ▶ **Fix `schemas.py`:** add `TestSummary`; change `HistoryResp` to `{tests: list[TestSummary]}`; confirm `ScoreObject` stores/returns `engagement` + `brain_frames` + `region_timeline` (already present ✅). (finding #1, #6)
- ▶ **Data-access layer:** `db/mongo.py` → `AsyncMongoClient`, one client per container (module scope / `@modal.enter()`), pool tuned for serverless (`maxPoolSize=5, minPoolSize=0, serverSelectionTimeoutMS=5000`); thin repository modules per collection (`users/tests/variants/scores`); one `ensure_indexes()` run on startup. (finding #8)
- ▶ **Implement all routes against `mocks/mock_score.py` + `mocks/mock_variants.py`:** create test, add variant, base-media, voice-variants (→ D stub), score (→ B stub), get test, history, explain (→ D stub). ID minting (`test_/var_/score_` + 12-hex). Full API serves fake data end-to-end.
  - **`/voice-variants` body is `{ base_media_key, variants: [VoiceSpec] }`** (CONTRACTS §5, updated 2026-07-18 — no longer `{script, voices}`). C validates each spec has a `script` → `bad_request` (§9) before calling D (D does a bare `spec["script"]`), then assigns `test_id`, persists, appends to `variant_ids`, returns `{ variants: [Variant] }`.
- ▶ **CORS** (`CORSMiddleware`, `ALLOWED_ORIGINS`) + **error envelope** (`{error:{code,message}}`, §9) + `/api/health`. (finding #5)
- ▶ **Media storage + serving (Modal wiring — findings #7, #12, #13):**
  - **Storage = the shared `reeled-in-cache` Modal Volume** at `/cache/media/<variant_id>.mp4` — this is the *only* place both C (uploads), D (overlay output), and B (`score_gpu` reads) can meet. Mount it on `api()`: `@app.function(image=image, volumes={CACHE_DIR: cache})`.
  - **One media root:** C owns a single resolver (`/cache/media`); B already uses it. D's `overlay.py`/`voice.py` must write there too (C passes the root, or copies D's output onto the Volume post-generation). Call `cache.commit()` after writes; a reader container may need `cache.reload()`.
  - **Serving is a proxy route, not signed URLs** — Modal Volumes have **no public URL**, so C streams bytes through FastAPI (`GET /api/media/{media_key}` → `FileResponse`/`StreamingResponse`, Range support for video). A loads video + brain PNGs from this route.

### Phase 2 — Real persistence & auth
- ▶ **Auth0 JWT verification** — **PyJWT + `PyJWKClient`** (NOT python-jose: abandoned, CVE-2024-33663/33664; FastAPI dropped it in 2024). Verify RS256 against JWKS with `audience=AUTH0_AUDIENCE` + `issuer`; module-scope `PyJWKClient` (caches keys, survives warm containers); FastAPI `Depends(get_current_user)` → `sub` (stable key) + `email`, upsert `users`. **Two gotchas:** (1) the frontend must send the **access token** (SPA SDK called with `audience`), not the id token — reject id tokens; (2) `email` isn't in an Auth0 access token by default — add it via a post-login Action custom claim (`https://.../email`), treat as best-effort. C-minted-session-JWT fallback (§6) kept ready. (finding #4; snippet in §11)
- ▶ Real Mongo persistence for tests/variants/scores; **async scoring (Pattern A — GPU owns status):** `POST /score` inserts the test `status=scoring` and calls `score_gpu.spawn(test_id, media_key)` (fire-and-forget, returns immediately — **not** `.remote()`, which would blow Modal's 150 s request cap). `score_gpu` calls `cache.reload()` (to see freshly-uploaded media), scores, and **writes `status=complete/failed` + scores straight to Mongo**. `GET /tests/{id}` is then a trivial Mongo read that A polls. Web layer stays stateless (survives container restarts; no `FunctionCall` bookkeeping).
- ▶ **Winner selection** at score time by `objective` — via a Mongo **aggregation pipeline** (§5), sets `winner_variant_id`.
- ▶ **Intelligence-layer orchestration (wire D's shipped code — see §5.2):**
  - `POST /api/suggest` `{ base_media_key, context? }` → `gemini.suggest(base_media_key, context)` → `{ variants: [VoiceSpec], rationale }` (now **required**, MLH Gemini track; feeds straight into `/voice-variants`).
  - On test completion, after setting the winner: `llm.record_test(user_id, test, variants, winner_variant_id)`; persist the returned thread id to `users.backboard_thread_id`.
  - `GET /tests/{id}/tips` → resolve `test_id → user_id` → `llm.tips(user_id)` → `{ tips }`.
  - `POST /tests/{id}/explain` → per variant, `explainer.explain(score.region_timeline)`; assemble `{ explanations: { "<variant_id>": [{t,text}] } }`.
  - **Media-root note:** D's `gemini`/`voice`/`overlay`/`llm` all resolve files under repo-root/`media` — when C runs them on Modal they must point at the shared Volume `/cache/media` (finding #12).
- ▶ `db/seed_demo.py`: load `demo/precomputed/*.json` (from B) into Mongo as `status=complete` rows so `GET /tests/{demo}` returns instantly on stage. The live `score_gpu.spawn()` path runs as a genuine background flourish but **gate it behind an env flag** so it never overwrites a curated demo score, and the demo never waits on A100 cold-start. (finding #10)

### Phase 3 — Integration (the only sequential part)
1. **C←B:** swap the score stub for `modal_app.score_gpu.remote(media_key)`.
2. **C←D:** swap the generation/LLM/explain stubs for D's real functions.
3. **C→A:** A points at C's live base URL; verify the polling loop + winner + media rendering end-to-end.
4. **C+B:** seed precomputed demo scores; verify `GET /tests/{demo}` returns exactly `mock_api.json`'s shape.

### Phase 4 — Hardening
- ▶ Make the precomputed path bulletproof (never depends on live GPU); `keep_warm` the ASGI container during judging; stable deploy; graceful nulls (`status=failed` → `score=null`, A handles it).

---

## 5. MongoDB "above-and-beyond" layer (the fun part)

Reeled In already commits to Atlas as system of record — this makes it a *showcase*, and a strong **MLH "Best Use of MongoDB Atlas"** entry. The **primary** MongoDB story is the **aggregation pipeline** (winner + array analytics, 5.1) plus a clean indexed schema — pure-C, zero overlap with other lanes. Vector/search (5.2/5.3) are **optional** and only make sense as *distinct* features now that D owns personalization via Backboard (see 5.2). Prioritized so each item is **both** demo-impressive **and** shippable. (Verified against 2025–2026 MongoDB docs; statuses noted.)

### 5.1 Server-side winner + curve analytics via the Aggregation Pipeline — *do first, Low risk, GA*
Compute the winner (and mean-attention / area-under-curve analytics) **inside Mongo** instead of pulling variants into Python. Directly satisfies "backend sets `winner_variant_id` at score time by `objective`":

```python
# winner = variant with the max metric named by the test's `objective`
pipeline = [
    {"$match": {"test_id": test_id}},
    {"$addFields": {
        "obj_score": {"$getField": {"field": objective, "input": "$metrics"}},
        "avg_visual":  {"$avg": "$networks.visual"},          # analytics straight off the arrays
        "auc_engage":  {"$reduce": {"input": "$engagement", "initialValue": 0,
                                     "in": {"$add": ["$$value", "$$this"]}}},
    }},
    {"$sort": {"obj_score": -1}},
    {"$group": {"_id": "$test_id",
                "winner_variant_id": {"$first": "$variant_id"},
                "ranking": {"$push": {"variant_id": "$variant_id", "obj_score": "$obj_score"}}}},
]
```
`$avg`/`$reduce`/`$map` run directly on the embedded network arrays — which is the payoff for keeping scores as **embedded arrays** (see 5.4). Highest ROI on the list; lifts the "Completeness" score for near-zero risk.

### 5.2 Personalization/memory is Backboard's job now (D shipped it) — Vector Search only if *distinct* — *reclassified: optional stretch, not headline*
> **Reconciliation update (reviewed against `dc6a73a`):** D has **shipped** the "learns your style" loop in `generation/llm.py` — one **Backboard thread per user**, `record_test(user_id, test, variants, winner)` writes each outcome into that thread (server-side memory), `tips(user_id)` reads personalized advice back. This is exactly the personalization I'd earlier proposed Atlas Vector Search for — so **building Vector Search RAG for tips would now duplicate working D code. Don't.** Backboard owns memory+tips; C *orchestrates* it (see below). The earlier "(a) C owns retrieval / (b) replace Backboard" fork is **resolved: neither — Backboard stays, C wires it.**

**What C actually owns here (not a new feature — plumbing D's memory loop):**
- Persist the thread map: add **`backboard_thread_id`** to the `users` doc (D's `llm.py` currently keeps it in a local JSON explicitly "until C's Mongo `users` doc takes over"). C reads/writes it; D's functions take/return the thread id.
- **On test completion** (in the score flow, right after C sets `winner_variant_id`): call `llm.record_test(user_id, test, variants, winner_variant_id)` so the memory learns.
- **`GET /tests/{id}/tips`:** resolve `test_id → user_id`, call `llm.tips(user_id)`, return `{ tips }`. (Tips are per-*user* memory even though the route hangs off a test — C bridges.)

**Atlas Vector Search — keep ONLY as an optional, non-overlapping stretch (MongoDB Atlas track depth):** a *semantic "find similar past tests"* browse feature (embed test summaries in `test_summaries`, `$vectorSearch` filtered by `user_id`) — distinct from Backboard's tips because it's retrieval-for-display, not advice generation. Ship the aggregation pipeline (5.1) as the primary MongoDB story; only add this if 5.1 + core routes are done and you want the extra Atlas-track surface. Adds `VOYAGE_API_KEY` (§8). **Default: skip** unless there's clear slack.

### 5.3 Atlas Search (BM25), optionally hybrid `$rankFusion` — *nice-to-have, Low→Med, GA — contingent on 5.2*
Only relevant if the optional 5.2 semantic-history feature is built: a `$search` index over `test_summaries` gives keyword history search, and `$rankFusion` fuses BM25 + `$vectorSearch` into one hybrid query. A genuine differentiator, but strictly clock-permitting and after the core routes + 5.1 land.

### 5.4 Storage shape decision — embedded arrays, **not** time-series collections — *validates current design*
The 5 network curves are fixed-length float arrays written **once** when scoring finishes, then read many times — a bounded blob on a variant, not an open-ended measurement stream. Mongo **Time Series collections** shine for continuous appends and carry update restrictions (can't update non-meta fields in place) that fight our write-once/occasionally-overwrite flow. **Keep the current embedded-array `scores` document** (`schemas.py` already does this ✅) — and it's what makes 5.1's array analytics trivial.

### 5.5 Live status — keep polling (per contract); Change Streams only as a stretch
`CONTRACTS §5` already specifies A polling `GET /tests/{id}`. Mongo **Change Streams** could push `pending→scoring→complete` in real time, but a change stream is a persistent blocking cursor that fits poorly on scale-to-zero Modal containers (and M0 support is ambiguous). Ship polling; mention change-streams-over-SSE as a "what's next" only.

### 5.6 Do **not** use
- **Atlas Data API / custom HTTPS endpoints** — **EOL Sept 30 2025** (removed). We have a real backend; don't build on it.
- **Atlas Triggers / App Services / Functions** — deprecated runtime; do server-side reactions in FastAPI.

---

## 6. Data model & indexes

Collections (`reeled_in`): `users`, `tests`, `variants`, `scores`; `test_summaries` only if building the optional 5.2. Keep `_id` as the prefixed string ID.
- **`users` gains `backboard_thread_id`** — C persists D's per-user Backboard thread id here (replacing D's local-JSON stand-in in `llm.py`). Written on first `record_test`, read for `tips`.

`ensure_indexes()` (run once on startup):
- `tests`: `{user_id: 1, created_at: -1}` (history), `{_id: 1}`.
- `variants`: `{test_id: 1}`.
- `scores`: `{test_id: 1}`, `{variant_id: 1}` (unique).
- `test_summaries`: a **vectorSearch** index on `embedding` (filter field `user_id`); optional **search** (BM25) index for 5.3.

---

## 7. Best-practices checklist (FastAPI + Mongo + Modal, 2025–2026)

- [ ] Driver = **PyMongo Async** (`from pymongo import AsyncMongoClient`); `await` all ops. Do **not** adopt Motor (deprecated). — finding #8
- [ ] **One client per container** (module scope or `@modal.enter()`), reused across warm requests; close in FastAPI `lifespan`. Never create a client per request.
- [ ] Pool tuned for serverless: `maxPoolSize=5, minPoolSize=0, serverSelectionTimeoutMS=5000, maxIdleTimeMS=10000`; Atlas cluster in the **same region** as the Modal app.
- [ ] **Pydantic v2** models with an ObjectId-free, prefixed-string `_id`; repository modules per collection; centralized `ensure_indexes()`.
- [ ] **CORS** = exact Base44 origin (**not `*`** — you send `Authorization`, so `allow_credentials=True` forbids `*`), `allow_headers=["Authorization","Content-Type"]`; add the middleware first. Error envelope `{error:{code,message}}`.
- [ ] **Auth0:** PyJWT `PyJWKClient` (module scope), RS256 + `audience`/`issuer` checks; accept the **access token only** (reject id tokens); `email` via a post-login-Action custom claim, best-effort.
- [ ] **Media:** serve with `FileResponse` (HTTP Range/206 for video seeking is free — don't hand-roll `StreamingResponse`); **writer `cache.commit()`, reader `cache.reload()`** for cross-container reads; mount the Volume on `api()`; `min_containers=1` on `api()` during judging so no cold start.
- [ ] **Scoring** off the request path: `score_gpu.spawn(...)` (never `.remote()` in a route — 150 s web cap); GPU fn writes status+score to Mongo.
- [ ] Store the **full Score Object** (incl. `engagement`, `brain_frames`, `region_timeline`).
- [ ] Winner + analytics in an **aggregation pipeline**, not Python.
- [ ] Verify on the actual Atlas cluster during setup: vector/search indexes build on **M0**; whether Automated Embedding is enabled before demo-depending on it.
- [ ] **Day-1 smoke test (do not defer):** from the *deployed* Base44 app, `fetch()` your Modal `/api/health` and run an Auth0 popup login end-to-end — Base44's CSP isn't per-app configurable and is undocumented for outbound calls, so prove it early. Bundle the Auth0 SDK via npm (not a CDN `<script>`) and use **popup** login (silent-iframe auth is fragile under CSP/ITP). Add the Base44 origin to Auth0 Allowed Callback/Web-Origin/Logout URLs.

---

## 8. Contract-change requests C must raise (don't edit `CONTRACTS.md` unilaterally)

Per the change process (§0 of `CONTRACTS.md`): edit the contract first, log it, announce — then code. C should raise these four:

1. **§5 — add a media route.** `GET /api/media/{media_key}` streaming bytes from the Modal Volume via `FileResponse` (no signed URLs — Volumes have no public URL). A cannot render video/brain-PNGs without it. *(High — blocks A at integration.)*
2. **§5/§6 — CORS is normative.** Document that C allows only `ALLOWED_ORIGINS`; A calls C cross-origin directly. *(High.)*
3. **§1 vs §3/§4 — resolve `id` vs `test_id`.** Clarify that a Test/Variant's **own** PK serializes as `id` (matching `mock_api.json` + `schemas.py`), and `test_id` is the foreign-key / `TestSummary` name. *(High — prevents a breaking "fix".)*
4. **§4 — `scores` doc must include `engagement`, `brain_frames`, `region_timeline`.** Update the sketch so persistence keeps what A renders. *(High.)*
5. *(If pursuing 5.2)* **§8 — add `VOYAGE_API_KEY`**; note the C-owns-retrieval / D-owns-generation boundary (or the decision to drop Backboard).

---

## 9. Dependencies (who feeds whom)

**C needs:**
- **A:** confirm A reads `test.id` (not `test_id`) and polls `GET /tests/{id}`; A's Base44 app origin(s) for `ALLOWED_ORIGINS`; Auth0 `domain/clientId/audience` (public) so C's `AUTH0_*` match.
- **B:** `score(media_key) -> ScoreObject` deployed as `modal_app.score_gpu`; `demo/precomputed/*.json` for `seed_demo`; keeps resolving `media_key` under the shared `/cache/media` root (already does ✅).
- **D (all shipped as of `dc6a73a`):** `generate_voice_variants(base_media_key, specs) -> [Variant]` (`test_id: None`, C assigns); `gemini.suggest(base_media_key, context) -> {variants, rationale}`; `llm.record_test(user_id, test, variants, winner) -> thread_id` + `llm.tips(user_id) -> str` (Backboard memory — C persists `backboard_thread_id`, calls `record_test` on completion); `explainer.explain(region_timeline) -> [{t,text}]`. **All must resolve media under the shared `/cache/media` Volume** (finding #12).

**C gives:**
- **A:** the live `/api` base URL + every route in §2, on-contract.
- **B/D:** ID minting, media storage/`media_key`s, Mongo persistence, and `user_id` from auth.

---

## 10. Applied in this pass / open decisions

**Applied now (unambiguous, C-owned, pure contract-sync):**
- `backend/.env.example` synced to `CONTRACTS §8` — removed `BACKEND_API_KEY`, added `ALLOWED_ORIGINS`, `AUTH0_DOMAIN`, `AUTH0_AUDIENCE` (finding #3).

**Resolved this pass (Modal-constrained, no longer open):**
- **Media serving = proxy route** (`GET /api/media/{media_key}`), *not* signed URLs — Modal Volumes expose no public URL, so bytes stream through FastAPI. (was open)
- **Media storage = the shared `reeled-in-cache` Volume** at `/cache/media`, mounted on `api()` too. (findings #12/#13)

**Open decisions for the team:**
- **Media root ownership (needs B+D sign-off):** confirm D writes generated variants to the shared Volume `/cache/media` (or hands files to C to place there), and that B keeps resolving `media_key` under the same root (it already does ✅). Without this, live generate→score breaks on Modal.
- ~~5.2 boundary~~ **RESOLVED (review of `dc6a73a`):** D shipped Backboard memory+tips (`llm.py`), so C **wires** it (persist `backboard_thread_id`, call `record_test` on completion, route `/tips`) — no Vector Search for personalization (would duplicate it). Vector Search stays only as an optional *distinct* semantic-search stretch.
- Auth: proceed with Auth0 (locked in §6) — confirm the SPA SDK loads inside the Public Base44 page (CSP) at the event.
- Hybrid `$rankFusion` search (5.3): only if the clock allows.

---

## 11. Verified implementation patterns (copy-paste starting points)

Current as of July 2026 (see §12 sources). These are the four pieces most likely to cost time if done wrong.

**Modal wiring — mount the Volume on `api()`, keep it warm:**
```python
cache = modal.Volume.from_name("reeled-in-cache", create_if_missing=True)

@app.function(image=image, volumes={CACHE_DIR: cache},        # ← the missing mount (finding #13)
              secrets=[modal.Secret.from_name("reeled-in")], min_containers=1)  # warm for judging
@modal.concurrent(max_inputs=100)
@modal.asgi_app()
def api():
    from backend.main import app as fastapi_app
    return fastapi_app
```

**Auth0 verify (PyJWT + PyJWKClient) — module scope, access-token only:**
```python
import os, jwt
from jwt import PyJWKClient
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

_ISSUER = f"https://{os.environ['AUTH0_DOMAIN']}/"
_jwks = PyJWKClient(f"{_ISSUER}.well-known/jwks.json", cache_keys=True, lifespan=300)
_bearer = HTTPBearer()
EMAIL_CLAIM = "https://reeledin.app/email"   # set by an Auth0 post-login Action

def current_user(creds: HTTPAuthorizationCredentials = Depends(_bearer)) -> dict:
    try:
        key = _jwks.get_signing_key_from_jwt(creds.credentials).key
        p = jwt.decode(creds.credentials, key, algorithms=["RS256"],   # whitelist alg
                       audience=os.environ["AUTH0_AUDIENCE"], issuer=_ISSUER,
                       options={"require": ["exp", "iat", "sub"]})
    except jwt.InvalidTokenError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"invalid token: {e}")
    return {"sub": p["sub"], "email": p.get(EMAIL_CLAIM)}   # sub = stable user key
```

**Media serve — `FileResponse` gives Range/206 (video seeking) for free; reload on miss:**
```python
from fastapi.responses import FileResponse
@router.get("/media/{media_key:path}")
def media(media_key: str):
    path = Path(CACHE_DIR) / media_key            # e.g. /cache/media/var_x.mp4
    if not path.exists():
        cache.reload()                            # reader reloads (cross-container writes)
        if not path.exists(): raise HTTPException(404)
    return FileResponse(path)                      # 206 Partial Content handled internally
```

**Async score — `spawn()` off the request path; the GPU fn owns status (Pattern A):**
```python
@router.post("/tests/{test_id}/score")
async def score(test_id: str, user=Depends(current_user)):
    await tests.update_one({"_id": test_id}, {"$set": {"status": "scoring"}})
    for v in await variants_for(test_id):
        score_gpu.spawn(test_id, v["media_key"])   # returns immediately (NOT .remote())
    return await test_doc(test_id)                  # A polls GET /tests/{id} for status flip
# score_gpu (GPU fn): cache.reload(); score(); write {status, scores, winner} to Mongo.
```

**PyMongo Async client — one per container, tuned for serverless:**
```python
from pymongo import AsyncMongoClient
_client = AsyncMongoClient(os.environ["MONGODB_URI"], maxPoolSize=5, minPoolSize=0,
                           serverSelectionTimeoutMS=5000, maxIdleTimeMS=10000)
db = _client[os.environ.get("MONGODB_DB", "reeled_in")]   # await db.tests.find_one(...)
```

---

## 12. Sources (verified 2025–2026)

**MongoDB:**
- Vector Search stage / overview: https://www.mongodb.com/docs/atlas/atlas-vector-search/vector-search-stage/ · https://www.mongodb.com/docs/atlas/atlas-vector-search/vector-search-overview/
- Voyage embeddings quickstart: https://www.mongodb.com/docs/voyageai/quickstart/ · Automated Embedding: https://www.mongodb.com/docs/vector-search/crud-embeddings/automated-embedding/
- Hybrid `$rankFusion`: https://www.mongodb.com/docs/manual/reference/operator/aggregation/rankfusion/
- Time-series considerations: https://www.mongodb.com/docs/manual/core/timeseries/timeseries-considerations/
- PyMongo Async vs Motor (migration): https://www.mongodb.com/docs/languages/python/pymongo-driver/current/reference/migration/
- Data API EOL: https://www.mongodb.com/docs/atlas/app-services/data-api/data-api-deprecation/

**Backend (Auth0 / Modal / Base44):**
- PyJWT + `PyJWKClient` (FastAPI dropped python-jose): https://pypi.org/project/PyJWT/ · https://github.com/fastapi/fastapi/discussions/9587
- Auth0 — validate access tokens (not id tokens): https://dev.auth0.com/docs/secure/tokens/access-tokens/validate-access-tokens · https://auth0.com/docs/libraries/auth0-single-page-app-sdk
- Modal Volumes (commit/reload) + web endpoints + timeouts: https://modal.com/docs/guide/volumes · https://modal.com/docs/guide/webhooks · https://modal.com/docs/guide/webhook-timeouts
- Modal `FunctionCall` / spawn / job-queue: https://modal.com/docs/reference/modal.FunctionCall · https://modal.com/docs/guide/job-queue
- Base44 security (CSP/CORS not per-app configurable): https://docs.base44.com/Setting-up-your-app/security-overview · FastAPI CORS: https://fastapi.tiangolo.com/tutorial/cors/
