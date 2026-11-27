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
# Which skill owns each station. The BA skill holds shape, spec and review; the Dev skill plans;
# publishing is optional and never runs on its own.
STATION_SKILL = {
    "shape": "sw-craft",
    "spec": "sw-craft",
    "review": "sw-craft",
    "plan": "sw-forge",
    "publish": "sw-ship",
}
# Skills whose run can end at a human decision (split acceptance, story acceptance). They go
# last, so every piece of work that needs no answer is finished before the run asks anything.
# Skills whose run ends at a human decision (split acceptance, story acceptance) go last, so
# every piece of work that needs no answer is finished before the run asks anything.
GATED = {"sw-craft"}
# sw-forge needs no answer inside itself, so it runs before the BA line, which ends at the
# owner's finalize. Crossing from craft into forge is the user's explicit request; a run
# never enters forge on its own.
FREE_ORDER = ("sw-forge",)
GATED_ORDER = ("sw-craft",)
BATCHABLE = {"spec": "sw-craft", "review": "sw-craft", "plan": "sw-forge"}


def annotate(root: Path, scope: str, rows: list[dict]) -> list[dict]:
    """Add the open blocking questions of each feature row (read from records, not the graph)."""
    base = workspace.scope_dir(root, scope)
    accepted = _accepted_epics(base)
    for row in rows:
        if row.get("kind") == "epic":
            row["split_accepted"] = row.get("id") in accepted
        if row.get("kind", "feat") == "feat" and ":FEAT-" in row.get("id", ""):
            feat = row["id"].split(":")[-1]
            found = blockers.blocking_questions(base, scope, feat)
            row["questions"] = [f"{qid} {title}".strip() for qid, title in found]
            story = base / "02-drafts" / f"{feat}.story.md"
            if story.is_file():
                fm = frontmatter.parse(story.read_text(encoding="utf-8")).fm or {}
                row["origin"], row["story_kind"] = fm.get("origin"), fm.get("kind")
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
        # station of its own any more, so it neither waits nor reruns sw-craft.
        if cond == "complete" or row.get("split_accepted"):
            return {"item": rid, "complete": True}
        if done == STATION_SKILL["shape"]:
            return {"item": rid, "wait": "decision", "why": "owner accepts or revises the split"}
        return {"item": rid, "skill": STATION_SKILL["shape"]}
    if station == "shape":
        if done == STATION_SKILL["shape"]:
            return {"item": rid, "wait": "decision", "why": "owner accepts the reopened slice"}
        return {"item": rid, "skill": STATION_SKILL["shape"]}
    if station == "spec":
        if cond == "not-started":
            # A draft with no story yet is work, not a failure: only a run that just wrote
            # stories and left none is a stop.
            if done == STATION_SKILL["spec"] and row.get("story_written"):
                return {
                    "item": rid,
                    "wait": "blocked",
                    "why": "the story step finished without a story",
                }
            return {"item": rid, "skill": STATION_SKILL["spec"]}
        if row.get("questions"):
            return {
                "item": rid,
                "wait": "input",
                "why": "answer blocking question " + "; ".join(row["questions"][:3]),
            }
        if done == STATION_SKILL["spec"]:
            # A finished draft goes to review on its own; submit-review is not approval and the
            # transition refuses while a blocking question is open or the review lint fails.
            return {"item": rid, "skill": STATION_SKILL["review"], "transition": "submit-review"}
        return {"item": rid, "skill": STATION_SKILL["spec"]}
    if station == "review":
        if done == STATION_SKILL["review"]:
            why = (
                "a configured approver's sign-off evidence"
                if signoff == "required"
                else "the owner's finalize of the review pack just shown"
            )
            return {"item": rid, "wait": "decision", "why": why}
        return {"item": rid, "skill": STATION_SKILL["review"]}
    if station == "plan":
        # Version 1 of an existing feature is already built: finalizing it ends its pipeline.
        if cond == "complete" or row.get("origin") == "as-is":
            return {"item": rid, "complete": True}
        if done == STATION_SKILL["plan"]:
            why = "; ".join(blockers) or "the task check still fails"
            return {"item": rid, "wait": "blocked", "why": why}
        return {"item": rid, "skill": STATION_SKILL["plan"]}
    if station == "publish":
        return {
            "item": rid,
            "wait": "decision",
            "why": "publication runs only in sw-ship, after the user asks and confirms its dry-run",
        }
    return {"item": rid, "wait": "blocked", "why": f"unknown station {station}"}


def _beyond(row: dict, plan: dict, until: str | None) -> bool:
    """True when the next station lies beyond the one the user asked to stop after.

    A transition names the station it moves into (submit-review leaves spec), so the limit is
    applied to where the work goes next, not where it stands now.
    """
    if not until:
        return False
    station = plan.get("transition") and "review" or row.get("station")
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
    example sw-craft for a draft idea that has no features yet.
    """
    plans = [_row_next(r, done, signoff) for r in rows]
    complete = [p["item"] for p in plans if p.get("complete")]
    waiting = [
        {"item": p["item"], "kind": p["wait"], "why": p["why"]} for p in plans if "wait" in p
    ]
    runnable = [p for p in plans if "skill" in p]
    by_item = {r["id"]: r for r in rows}
    held = [p for p in runnable if _beyond(by_item.get(p["item"], {}), p, until)]
    runnable = [p for p in runnable if not _beyond(by_item.get(p["item"], {}), p, until)]

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
        answer.update(mode="stop", reason="nothing on the board to advance; route with sw-start")
        return answer
    if not runnable:
        if waiting:
            answer.update(mode="stop", reason="waiting for the user: " + _summary(waiting))
        elif held:
            answer.update(mode="stop", reason=f"stopped after {until}, as asked")
        elif done == "sw-craft":
            # The BA role is over. The Dev role is a separate request, never a next station.
            forge = sorted({p["item"] for p in plans if p.get("skill") == "sw-forge"})
            answer.update(
                mode="done",
                reason="BA line finished: accepted stories, tasks and prompts are the delivery",
                say=(
                    f"Accepted: {', '.join(forge)}. Say **forge** to plan "
                    + (", ".join(forge) if forge else "a story")
                    + "."
                    if forge
                    else "Accepted. Nothing is left in the BA line."
                ),
                plan_next=forge,
            )
        else:
            answer.update(
                mode="done",
                reason="pipeline finished: story, plan, tasks and agent prompts are the delivery",
            )
        return answer

    # Work that needs no answer first, in lifecycle order; stations that end in a question last.
    # sw-forge is the only skill that needs no answer inside itself, so it runs before the BA
    # line, which ends in the owner's finalize.
    order = [s for s in FREE_ORDER + GATED_ORDER]
    chosen = min(runnable, key=lambda p: order.index(p["skill"]) if p["skill"] in order else 99)
    skill = chosen["skill"]
    batch = [p for p in runnable if p["skill"] == skill]
    # A finished BA run hands its accepted stories over instead of looping: its remaining
    # items all need the review step again, so the hand-off is the stop, not a failure.
    hand_over = done == skill and done != "sw-craft"
    if hand_over and not any(p.get("transition") for p in batch):
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
        answer["after"] = sorted(
            {p["skill"] for p in later}, key=lambda s: order.index(s) if s in order else 99
        )
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
        "sw-craft": "the BA line: satisfy its gates, then ask the owner to accept",
        "sw-forge": "write the detailed plan, set the task statuses and generate the prompts",
        "sw-ship": "publish only after the user asks",
    }.get(skill, "run the station")
    if any(p.get("transition") for p in batch):
        what = "submit the finished drafts (not approval), then " + what
    return f"{skill} for {ids}: {what}" + ("" if named else " (whole scope, station by station)")
