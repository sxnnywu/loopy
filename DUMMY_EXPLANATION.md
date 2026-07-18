# Loopy, Explained Like You're New Here

## The one-liner

Loopy is a testing lab for AI agent systems that run in loops. It clones an agent system a thousand times, lets every clone run in its own sealed sandbox, records every message the agents send each other, and then tells you where the loop breaks, drifts, stalls, or wastes money.

## Back up — what is "loop engineering"?

Normally, a person prompts an AI agent, reads the answer, prompts again. Loop engineering removes the person: you design a system that prompts, evaluates, and re-prompts the agents automatically. The agents talk to each other in structured loops until the job is done. Companies build these for things like customer-support voice agents, fintech transaction workflows, and internal automation.

## The problem

Nobody has a good way to QA these loops.

- A loop that works once might fail on run #47 for reasons no one can reproduce.
- Two agents can get stuck politely handing a task back and forth forever.
- Small prompt or model changes can silently change loop behavior.
- Watching one run tells you almost nothing; the failures are statistical.

## What Loopy does

1. **Ingest** — you point Loopy at a loop-engineered agent system (its agents, prompts, and workflow definition).
2. **Fan out** — Loopy spins up a large number of isolated sandboxes (target: 1,000) and runs the same loop in every one, optionally with varied inputs.
3. **Capture** — every agent-to-agent message, tool call, retry, and state change in every sandbox is recorded to a central store.
4. **Analyze** — Loopy aggregates the runs: convergence rate, loop-stall detection, divergence between runs, token/cost stats, failure clustering.
5. **Report** — you get a dashboard and a QA report: "here is where your loop breaks, how often, and why."

## Why sandboxes

Isolation. Each run is hermetic, so failures are attributable and runs can't contaminate each other. And scale: one run is an anecdote, a thousand runs are a dataset.

## Who it's for

Any team shipping multi-agent or loop-engineered systems: voice-agent companies, fintech workflow teams, B2B automation builders — anyone who needs to answer "does our loop actually behave?" with data instead of vibes.
