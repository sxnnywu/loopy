# Platform Research — Base44

**Role in Loopy:** the **dashboard / report-viewer front-end** — fleet status view, live agent-to-agent traffic feed, and the QA report view. Owned by the Interface & Design workstream.

**Goal of this doc:** use Base44 past its no-code defaults — **code mode, backend functions, GitHub sync** wired to our real FastAPI + WebSocket backend — so the dashboard looks intentional, not template-generated.

---

## Product overview (2026 state)
Base44 is an AI full-stack app builder (prompt → working app) with a built-in database, authentication, and integrations. Acquired by **Wix (~$80M, 2025)**. It's positioned for real full-stack apps, not just prototypes.

## Capabilities & latest features (changelog)
- **Built-in IDE / code mode** — hand-edit generated code for precise control (past prompt-only generation).
- **Backend functions** — custom server-side logic for internal tools / custom UIs.
- **Built-in database + auth** — data + users out of the box.
- **Integrations / one-click connectors** — **GitHub two-way sync**, Zapier, WhatsApp, NPM package support, **Stripe** (updated Jan 2026).
- **Debug mode + network logger** (Jan 2026) — inspect requests, debug wiring.
- **Dev/production separation + safe publishing** (Jan 2026) — protect the demo build.
- **Mobile app creation & publishing** (Feb 2026).
- **Enterprise:** workspace SSO, custom permissions, file-locking, custom domains/subdomains, app security dashboard, analytics.

## How Loopy uses it "above and beyond"
1. **Base44 as the front-end, MongoDB as the source of truth.** We do **not** store QA data in Base44's built-in DB — Mongo owns that. Base44's **backend functions** act as a thin proxy/BFF to our FastAPI routes and WebSocket, so the dashboard reads live data from the real backend. Showing we drew that line deliberately (not dumping data into the app builder's DB) is the sophistication signal.
2. **Code mode for the two hard components.** Prompt-generation is fine for layout, but the **live fleet grid** (hundreds of sandbox cells changing state) and the **streaming traffic feed** need hand-tuning — use the built-in IDE to wire the WebSocket and control render performance, rather than accepting the generated default.
3. **GitHub two-way sync** so the dashboard lives in the *same repo* as the backend — one source tree for a 4-person hackathon team, clean diffs, no "where's the frontend code" problem.
4. **Network logger** to debug the WebSocket / API wiring fast during integration (Phase 2), and **dev/production separation** so the rehearsed demo build is frozen and protected while others keep editing.
5. **Mock-first.** Per the Interface plan, build all three views against fake contract-shaped data in Base44 first, then swap to real endpoints — so the front-end is never blocked on the backend.

### Bonus: the Base44 "Venture Builder" prize angle
Base44's own track ($2,000/$1,000) rewards a **launched** product with **evidence of customer value**. If we host a public landing + waitlist for Loopy on Base44 (its Stripe/connector/deploy stack makes this trivial), the same build that renders our dashboard also becomes the validation surface — a legitimate second prize entry off one tool.

## Why Base44, and why this way
Chosen because the Interface workstream is **presenter/designer-led**, and Base44 is the fastest path from design templates to a polished, real dashboard — *but* we push it past no-code defaults (code mode + backend functions + GitHub sync) to integrate a genuine external backend, which is what separates "app-builder demo" from "real product." It anchors the Interface workstream and opens the Venture Builder track.

## Sources
- [Base44 changelog](https://base44.com/changelog) · [Developer changelog](https://docs.base44.com/changelog/developers) · [Base44 review 2026 (No Code MBA)](https://www.nocode.mba/articles/base44-review) · [Base44 + Wix explainer](https://www.certifiedcode.us/resources/article/what-is-base44-app-builder-and-how-does-it-work-with-wix) · [Full-stack tutorial](https://www.nocode.mba/articles/base44-ultimate-guide)
