"""Decide what happens after a station finishes: continue on, confirm, or stop for the user.

The decision is computed from saved files (the lifecycle board), never from chat memory, so it
gives the same answer whichever skill asks and whichever state the work is in. It never writes a
spec file, never approves and never publishes: it only names the next local skill and the
lifecycle actions the agent may take on its own, or the reason the run has to stop.

Modes in the answer:

- ``continue``: under ``flow: auto`` load ``next_skill`` now, in the same turn, and run it for
  ``items``. ``transitions`` lists local, non-approving lifecycle actions to apply first
  (only ``submit-review``); the agent previews and confirms each token itself.
- ``confirm``: under ``flow: guided`` ask one "Continue to <next_skill>? (Y/n)" first.
- ``stop``: a human decision, a missing input or a blocker; ``reason`` and ``waiting`` say which.
- ``done``: the local pipeline is finished; the Markdown story, plan and tasks are the delivery.
"""

from __future__ import annotations

from pathlib import Path

from kitlib import blockers, frontmatter, schema, workspace

STATION_ORDER = ("shape", "spec", "review", "plan", "publish")
# Skills whose run ends at a human decision (split acceptance, story acceptance). They go last,
# so every piece of work that needs no answer is finished before the run asks anything.
GATED = {"sw-shape", "sw-review"}
FREE_ORDER = ("sw-spec", "sw-plan")
GATED_ORDER = ("sw-shape", "sw-review")


def annotate(root: Path, scope: str, rows: list[dict]) -> list[dict]:
    """Add the open blocking questions of each feature row (read from records, not the graph)."""
    base = workspace.scope_dir(root, scope)
    accepted = _accepted_epics(base)
    for row in rows:
        if row.get("kind") == "epic":
            row["split_accepted"] = row.get("id") in accepted
        if row.get("kind", "feat") == "feat" and ":FEAT-" in row.get("id", ""):
            found = blockers.blocking_questions(base, scope, row["id"].split(":")[-1])
            row["questions"] = [f"{qid} {title}".strip() for qid, title in found]
    return rows


def _accepted_epics(base: Path) -> set[str]:
    """Epics whose feature split the owner accepted (an accepted DEC of subtype accepted-split)."""
    found: set[str] = set()
    for path in sorted((base / "records").glob("DEC-*.md")):
        fm = frontmatter.parse(path.read_text(encoding="utf-8")).fm or {}
        if fm.get("subtype") == "accepted-split" and fm.get("status") == "accepted":
            epics = fm.get("epics") or []
            found.update(str(e) for e in (epics if isinstance(epics, list) else [epics]))
    return found


def _row_next(row: dict, done: str | None, signoff: str) -> dict:
    """What one board row needs next: a skill to run, or a reason to wait."""
    rid, station, cond = row["id"], row.get("station", "spec"), row.get("condition", "unknown")
    kind = row.get("kind", "feat")
    blockers = list(row.get("blockers") or [])
    if cond == "unknown":
        return {"item": rid, "wait": "blocked", "why": "; ".join(blockers) or "unknown state"}
    if kind == "epic":
        # Once the split is accepted the epic's work continues in its features; it is not a
        # station of its own any more, so it neither waits nor reruns sw-shape.
        if cond == "complete" or row.get("split_accepted"):
            return {"item": rid, "complete": True}
        if done == "sw-shape":
            return {"item": rid, "wait": "decision", "why": "owner accepts or revises the split"}
        return {"item": rid, "skill": "sw-shape"}
    if station == "shape":
        if done == "sw-shape":
            return {"item": rid, "wait": "decision", "why": "owner accepts the reopened slice"}
        return {"item": rid, "skill": "sw-shape"}
    if station == "spec":
        if cond == "not-started":
            if done == "sw-spec":
                return {"item": rid, "wait": "blocked", "why": "sw-spec finished without a story"}
            return {"item": rid, "skill": "sw-spec"}
        if row.get("questions"):
            return {
                "item": rid,
                "wait": "input",
                "why": "answer blocking question " + "; ".join(row["questions"][:3]),
            }
        if done == "sw-spec":
            # A finished draft goes to review on its own; submit-review is not approval and the
            # transition refuses while a blocking question is open or the review lint fails.
            return {"item": rid, "skill": "sw-review", "transition": "submit-review"}
        return {"item": rid, "skill": "sw-spec"}
    if station == "review":
        if done == "sw-review":
            why = (
                "a configured approver's sign-off evidence"
                if signoff == "required"
                else "the owner's plain accept of the table just shown"
            )
            return {"item": rid, "wait": "decision", "why": why}
        return {"item": rid, "skill": "sw-review"}
    if station == "plan":
        if cond == "complete":
            return {"item": rid, "complete": True}
        if done == "sw-plan":
            why = "; ".join(blockers) or "the task check still fails"
            return {"item": rid, "wait": "blocked", "why": why}
        return {"item": rid, "skill": "sw-plan"}
    if station == "publish":
        return {
            "item": rid,
            "wait": "decision",
            "why": "publication runs only in sw-publish after a fresh yes to its dry-run",
        }
    return {"item": rid, "wait": "blocked", "why": f"unknown station {station}"}


def _beyond(skill: str, until: str | None) -> bool:
    """True when running skill would pass the station the user asked to stop after."""
    if not until:
        return False
    station = skill.removeprefix("sw-")
    if station not in STATION_ORDER or until not in STATION_ORDER:
        return False
    return STATION_ORDER.index(station) > STATION_ORDER.index(until)


def decide(
    rows: list[dict],
    flow: str = schema.DEFAULT_GOVERNANCE["flow"],
    signoff: str = schema.DEFAULT_GOVERNANCE["signoff"],
    done: str | None = None,
    until: str | None = None,
    named: bool = False,
    fallback: str | None = None,
) -> dict:
    """Pick the next step for the board rows of one item (named) or one scope.

    fallback is the routed skill (from sw-start) to continue with when the board is empty, for
    example sw-shape for a draft idea that has no features yet.
    """
    plans = [_row_next(r, done, signoff) for r in rows]
    complete = [p["item"] for p in plans if p.get("complete")]
    waiting = [
        {"item": p["item"], "kind": p["wait"], "why": p["why"]} for p in plans if "wait" in p
    ]
    runnable = [p for p in plans if "skill" in p]
    held = [p for p in runnable if _beyond(p["skill"], until)]
    runnable = [p for p in runnable if not _beyond(p["skill"], until)]

    answer = {
        "flow": flow,
        "done": done,
        "until": until,
        "complete": complete,
        "waiting": waiting,
        "held_by_until": [p["item"] for p in held],
        "next_skill": None,
        "items": [],
        "transitions": [],
    }
    if not rows:
        if fallback and fallback.startswith("sw-") and fallback != done:
            answer.update(mode="continue", next_skill=fallback, reason=f"{fallback}: routed")
            return _apply_flow(answer)
        if done == "sw-ingest":
            answer.update(mode="continue", next_skill="sw-start", reason="sources saved; re-route")
            return _apply_flow(answer)
        answer.update(mode="stop", reason="nothing on the board to advance; route with sw-start")
        return answer
    if not runnable:
        if waiting:
            answer.update(mode="stop", reason="waiting for the user: " + _summary(waiting))
        elif held:
            answer.update(mode="stop", reason=f"stopped after {until}, as asked")
        else:
            answer.update(
                mode="done",
                reason="pipeline finished: story, plan, tasks and agent prompts are the delivery",
            )
        return answer

    # Work that needs no answer first, in lifecycle order; stations that end in a question last.
    order = [s for s in FREE_ORDER + GATED_ORDER]
    chosen = min(runnable, key=lambda p: order.index(p["skill"]) if p["skill"] in order else 99)
    skill = chosen["skill"]
    batch = [p for p in runnable if p["skill"] == skill]
    if done and done == skill and not any(p.get("transition") for p in batch):
        answer.update(
            mode="stop",
            reason=f"no progress: {skill} just ran and the same items still need it; inspect",
            items=[p["item"] for p in batch],
        )
        return answer
    answer.update(
        mode="continue",
        next_skill=skill,
        items=[p["item"] for p in batch],
        transitions=[
            {"item": p["item"], "action": p["transition"]} for p in batch if p.get("transition")
        ],
        gated=skill in GATED,
        reason=_reason(skill, batch, named),
    )
    later = [p for p in runnable if p["skill"] != skill]
    if later:
        answer["after"] = sorted({p["skill"] for p in later}, key=order.index)
    return _apply_flow(answer)


def _apply_flow(answer: dict) -> dict:
    """auto continues, guided asks once per station, step stops and names the next station."""
    if answer.get("mode") != "continue":
        return answer
    if answer["flow"] == "guided":
        answer["mode"] = "confirm"
        answer["ask"] = f"Continue to {answer['next_skill']}? (Y/n)"
    elif answer["flow"] == "step":
        answer["mode"] = "stop"
        answer["reason"] = f"flow: step; name the next station ({answer['next_skill']}) to go on"
    return answer


def _summary(waiting: list[dict]) -> str:
    parts = [f"{w['item']} ({w['why']})" for w in waiting[:5]]
    more = f"; and {len(waiting) - 5} more" if len(waiting) > 5 else ""
    return "; ".join(parts) + more


def _reason(skill: str, batch: list[dict], named: bool) -> str:
    ids = ", ".join(p["item"] for p in batch)
    what = {
        "sw-shape": "shape, then ask the owner to accept the split",
        "sw-spec": "write or resume the story drafts",
        "sw-review": "check the drafts, then ask the owner to accept them",
        "sw-plan": "write the plan and tasks",
    }.get(skill, "run the station")
    if any(p.get("transition") for p in batch):
        what = "submit the finished drafts (not approval), " + what
    return f"{skill} for {ids}: {what}" + ("" if named else " (whole scope, station by station)")
