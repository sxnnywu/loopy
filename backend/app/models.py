# backend/app/models.py
#
# MIRROR of SHARED_CONTRACTS.md §1–§3 (the single source of truth).
# Person A owns the *canonical* shared-models module for the repo. Until that
# lands, Person C (analysis) uses this local mirror so we are not blocked.
# When A commits the shared module, change our imports to point at it and
# delete this file. Field names / types here must stay byte-for-byte identical
# to SHARED_CONTRACTS.md — never diverge silently.
from __future__ import annotations  # lets us use `str | None` on Python 3.9

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

# ── §1 Enums & String Literals ────────────────────────────────────────────
SandboxState = Literal[
    "pending", "provisioning", "running",
    "completed", "failed", "stalled", "timed_out",
]

EventType = Literal[
    "agent_message",   # one agent -> another agent
    "tool_call",       # agent invoked a tool
    "tool_result",
    "loop_iteration",  # loop tick boundary
    "state_update",    # Backboard.io memory write
    "termination",     # loop ended (carries reason)
    "error",
]

TerminationReason = Literal[
    "goal_reached", "max_iterations", "stall_detected", "timeout", "error",
]

FindingSeverity = Literal["info", "warning", "critical"]

# ── §2 Shared Constants ───────────────────────────────────────────────────
DEFAULT_MAX_ITERATIONS = 30
DEFAULT_SANDBOX_TIMEOUT_S = 300
DEFAULT_FLEET_SIZE_MVP = 50
STALL_WINDOW = 5           # iterations with no state progress = stalled
EVENT_BATCH_SIZE = 25      # events per collector POST
DASHBOARD_POLL_MS = 2000   # if polling; WebSocket preferred


# ── §3 Core Document Shapes ───────────────────────────────────────────────
class AgentDef(BaseModel):
    agent_id: str
    name: str
    model: str                       # e.g. "gemini-3.1-flash-lite"
    system_prompt: str
    tools: list[str] = []


class LoopSpec(BaseModel):
    spec_id: str
    name: str
    agents: list[AgentDef]
    topology: list[dict]             # edge shape {from_agent, to_agent, condition}
    termination: dict                # {max_iterations, goal_check}
    created_at: datetime


class RunBatch(BaseModel):
    run_id: str
    spec_id: str
    n_sandboxes: int
    seed_strategy: str               # "identical" | "varied"
    state: str                       # aggregate state
    created_at: datetime


class SandboxRun(BaseModel):
    sandbox_id: str
    run_id: str
    state: SandboxState
    seed_input: Optional[dict] = None
    iterations: int = 0
    termination_reason: Optional[TerminationReason] = None
    total_tokens: int = 0
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None


class Event(BaseModel):
    event_id: str
    run_id: str
    sandbox_id: str
    seq: int                         # per-sandbox monotonic sequence
    type: EventType
    ts: datetime
    from_agent: Optional[str] = None
    to_agent: Optional[str] = None
    payload: dict = {}               # type-specific body
    tokens: int = 0


class Finding(BaseModel):
    finding_id: str
    run_id: str
    severity: FindingSeverity
    title: str
    description: str
    evidence_sandbox_ids: list[str] = []
    stat: Optional[dict] = None      # e.g. {"stall_rate": 0.18}


class Report(BaseModel):
    report_id: str
    run_id: str
    summary: str
    findings: list[Finding] = []
    stats: dict = {}                 # completion_rate, histogram, cost, divergence
    created_at: datetime
