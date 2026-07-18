# Platform Research — MongoDB Atlas

**Role in Loopy:** the central store for all sandbox interaction data — every `Event`, `SandboxRun`, `RunBatch`, `LoopSpec`, `Report` — plus the aggregation engine behind the QA findings.

**Goal of this doc:** use Atlas the way a team that knows it *beyond CRUD* would — **Time Series collections** for events, **Change Streams** for the live feed, and **Vector Search** for failure clustering — not just "store JSON in a normal collection and poll it."

---

## Product overview (2026 state)
MongoDB Atlas is the managed cloud MongoDB platform. Beyond a document database it now bundles full-text search, vector search, time-series storage, change streams, stream processing, and queryable encryption — one platform covering storage + live + semantic search.

## Three features that upgrade Loopy (the "above and beyond")

### 1. Time Series Collections → the `events` store
Events are exactly high-volume, timestamped, sequential data — the textbook time-series case.
```javascript
db.createCollection("events", {
  timeseries: { timeField: "ts", metaField: "meta", granularity: "seconds" }
});
// meta: { run_id, sandbox_id }   ← tags we always filter by
```
Benefits: **automatic bucketing/compression (~90% storage reduction)**, fast timestamp range queries, and TTL for auto-expiry of old runs. This is the sophisticated choice vs. a plain collection, and it scales cleanly to 1,000 sandboxes × many events each.
> Keep the `(run_id, sandbox_id, seq)` and `(run_id, type)` indexes from `SHARED_CONTRACTS.md §4` for the exact-lookup query routes; time-series handles the volume/range side.

### 2. Change Streams → the live dashboard feed (replaces polling)
Instead of the dashboard polling every `DASHBOARD_POLL_MS`, the WebSocket layer taps a change stream and **pushes** new events/state transitions the instant they're inserted.
```javascript
const stream = db.collection("events").watch(
  [{ $match: { operationType: "insert" } }],
  { fullDocument: "updateLookup" }
);
stream.on("change", c => ws.broadcast(sampleForFeed(c.fullDocument)));
```
Filterable by op type, resumable after failures via **resume tokens** (so a dropped WebSocket reconnects without missing events). This is the elegant "we know Mongo" move — it makes the live fleet + traffic feed real-time instead of laggy polling.

### 3. Atlas Vector Search → rigorous failure clustering
Rather than eyeballing which failures are "the same," embed each failure/termination transcript, store the vector, and cluster with vector search — this is how "9 of 11 stalls involve the risk↔settle bounce on multi-currency inputs" gets *discovered*, not guessed.
- **Quantization** (scalar ~75%, binary ~97% memory reduction; `int8`/`int1`) keeps the vector index cheap.
- **Flat index** (preview) suits our per-run (multitenant-ish) clustering.
- **Lexical prefilters** narrow by `severity`/`type`/time before the vector step.
- **Native `$rerank`** (June 2026, Voyage AI models) refines cluster membership.
```javascript
db.failures.aggregate([
  { $vectorSearch: { path: "vector", queryVector: emb, numCandidates: 200, limit: 50,
      filter: { termination_reason: { $in: ["stall_detected","error"] } } } },
  { $rerank: { modelProvider: "voyageai", model: "rerank-2", topK: 10 } }
]);
```

## Aggregation pipelines (the deterministic core)
Completion rate, iteration histogram, cost (token) distribution, divergence across identical-seed pairs, and per-handoff failure rates are all `$group`/`$bucket`/`$facet` pipelines over `events` + `sandbox_runs`. **Math decides, the LLM only narrates** — deterministic stats first, Gemini clustering second.

## Why MongoDB, and why this way
Chosen because one platform covers all three shapes Loopy needs: **flexible event documents** (schema per event type), **time-series** for volume, **change streams** for the live feed, and **vector search** for semantic clustering. A relational DB would need bolt-ons for the last three. Also an MLH track (Best Use of MongoDB Atlas), so non-trivial usage (time-series + change streams + vector) is a strong prize entry, not a checkbox.

> **Build order:** connection + collections + indexes → collector writing to the time-series `events` → change-stream WebSocket → aggregation pipelines → vector clustering. Index *before* scale-testing, never after.

## Sources
- [Atlas changelog](https://www.mongodb.com/docs/atlas/release-notes/changelog/) · [Search & Vector Search changelog](https://www.mongodb.com/docs/atlas/search-changelog/) · [Atlas Vector Search + Confluent (real-time)](https://www.mongodb.com/company/blog/mongodb-atlas-vector-search-makes-real-time-ai-reality-confluent) · [Queryable Encryption expands search](https://www.mongodb.com/company/blog/product-release-announcements/queryable-encryption-expands-search-power) · [Atlas platform](https://www.mongodb.com/products/platform/atlas-database)
