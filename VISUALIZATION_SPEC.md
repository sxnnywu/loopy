# Visualization Spec — Results screen (single source for A)

**Owner of this doc:** C (Seb). **Implements:** A (Kimi). **Science source:** `SCORING_SCIENCE.md` §6–§7. **Binding rules:** `CONTRACTS.md` §3a.

Why this exists: the Results screen currently shows the same "winner + 4 metrics + retention%" for everything, but the science says a **single video is a profile (no grade)** and a **comparison ranks on real signals, not the composite metrics** — and the metrics are **[0,1] proxy scores, not percentages**. This doc is the exact build sheet to fix that. The backend now hands you an `analysis` object so you don't have to re-derive any of it.

---

## 1. The new backend field: `analysis` (in `GET /tests/{id}`)

The response is now `{ test, variants, scores, analysis }`. **Branch the whole Results screen on `analysis.mode`.**

```jsonc
// SINGLE video (1 variant):
"analysis": { "mode": "profile" }

// COMPARISON (2+ variants), once scored:
"analysis": {
  "mode": "comparison",
  "objective": "overall",                       // metric currently deciding the winner
  "ranking": [                                   // sorted, winner first
    { "variant_id": "var_…B", "label": "B", "score": 0.8026 },
    { "variant_id": "var_…A", "label": "A", "score": 0.7768 }
  ],
  "network_advantage": {                          // winner minus runner-up, mean per network
    "default_mode": 0.15, "visual": 0.03, "language": -0.01, "auditory": 0.0, "motion": 0.02
  },
  "decisive_network": "default_mode",            // the network that most separated them
  "signal_advantage": null                        // reserved — production signals (see §5), not live yet
}
```
`ranking[0].variant_id` always equals `test.winner_variant_id`. In a 2+ test that isn't finished scoring yet, `analysis` is just `{ mode, objective }` (no ranking) — show a "scoring…" state.

---

## 2. Profile mode (`mode === "profile"`) — a picture, NOT a grade

A single clip is a **predicted brain-response profile**. Nothing is compared; "more activation ≠ better." **Show only:**
- The video player.
- The **5 network curves** + the **engagement** curve (all from `scores[0]`).
- The **brain-frame flipbook** (`scores[0].brain_frames`) synced to `region_timeline` captions (once `/explain` is wired; until then show the raw `top_network`/`top_region`).

**Do NOT render, in profile mode:** `overall`, any winner/badge, a letter/number grade, or `retention`. (`overall`/`winner_variant_id` may exist in the payload — ignore them here.)

**Framing copy:** headline "How a viewer's brain would respond to this clip." One caveat line: *"A directional neural proxy — not ground truth."*

---

## 3. Comparison mode (`mode === "comparison"`) — ranking, with the science shown

- **Winner badge:** `ranking[0].label`.
- **Engagement curves overlaid** for all variants on one time axis (from each `scores[i].engagement`).
- **"Which brain system separated them" bars:** one bar per network from `network_advantage`, sorted by value; highlight `decisive_network`. Positive = winner stronger.
- **"Why this ranking" panel (required):** take `decisive_network`, look it up in the copy map (§4), render its one-liner + citation. This is the credibility piece — per §6, "the ranking is only credible if the research behind it is shown alongside it."
- **Metrics** (if shown at all): render as **proxy scores** (`0.79`, or a 0–1 dial), **labeled "proxy score."** See §6.

---

## 4. Network → rationale copy map (paste into the frontend, from `SCORING_SCIENCE.md` §2–§3)

Keyed by network name (`decisive_network` and the bar labels):

| key | Label | One-liner for the "why" panel | Cite |
|---|---|---|---|
| `default_mode` | **Meaning & narrative** | "The brain's default-mode network — narrative pull and self-relevance. It dominates responses to evolving stories and carries the value signal that predicts sharing, so it's our strongest engagement signal." | [14][7][5] |
| `visual` | **Faces & imagery** | "Faces and on-screen imagery. The fusiform face area is a dedicated face region and faces capture attention even when irrelevant — a reliable attention driver in face-heavy short-form." | [16][17] |
| `language` | **Speech & captions** | "Speech and caption comprehension — a high-level associative signal (where the brain model's edge is largest), when the clip is speech-driven." | [1] |
| `auditory` | **Sound & music** | "Music, sound design, audio texture. Near-universal and low-level — almost any audio drives it, so it's least discriminative of quality." | [1] |
| `motion` | **Cuts & action** | "Movement and edit pacing. Responds to almost any motion — and per short-form research, *more* pacing can *hurt* sustained engagement, so 'moved more' isn't automatically better." | [1][25] |

(Citation numbers map to `SCORING_SCIENCE.md`'s Sources list.)

---

## 5. ⚠️ Open dependency — §7's full comparison basis (needs B)

`SCORING_SCIENCE.md` §7 (added 2026-07-18) says a comparison should rank on **two families of signal**:
- **A. The 5 brain networks** — ✅ available, surfaced now as `network_advantage`.
- **B. Observable production signals** — facial expression, hand gestures, speech rate, motion, clarity. B *measures* these (`analyze_objective`), but they are **not in the Score Object yet**, so they're not in `analysis`. The `signal_advantage` field is the reserved slot.

**Until B adds family B to the Score Object (a §3 contract change) and we define a signal-based winner:** the winner + `ranking` are decided by the test's `objective` metric (interim), and the "why" panel shows the **brain-network** deltas only. This is a known, documented gap — build the network-delta panel now; family-B bars slot into the same component when `signal_advantage` goes non-null.

**Also (B):** `retention` saturates at 1.0 for any rising clip (clamp) — don't use it as the objective for winners; `overall` is the current default. B owns the formula fix.

---

## 6. Metrics are proxy scores, not percentages (applies everywhere)

- Never render `retention: 1.0` as "100% retention" or `overall: 0.69` as a "69% grade."
- They're normalized **directional-proxy** values in [0,1] (`SCORING_SCIENCE.md` §5). `retention` is a *ratio* of final-third ÷ first-third engagement, clamped at 1.0 (1.0 = "held or grew," not "perfect").
- Present as `0.69` / a 0–1 dial / a relative bar — with the wording "proxy score," and lead the screen with the "directional proxy, not ground truth" caveat.

---

## 7. A's build checklist
- [ ] Branch Results on `analysis.mode`.
- [ ] Profile: curves + engagement + flipbook + region timeline; **remove** metrics cards / winner / grade; add caveat copy.
- [ ] Comparison: winner badge, overlaid engagement curves, `network_advantage` bars (highlight `decisive_network`), "why this ranking" panel from §4, metrics as proxy scores.
- [ ] Kill every "%" on a metric; relabel as proxy scores.
- [ ] `signal_advantage` currently `null` — render the family-B bars conditionally so they appear automatically when B ships it.
- [ ] Dev against the updated `frontend/mock_api.json` (now carries an illustrative `analysis` block).
