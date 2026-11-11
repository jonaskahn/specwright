"""Read-only task coverage and planning checks shared by board, CLI and publish."""

from pathlib import Path

from kitlib import frontmatter, hashing, ids, markdown

APPROVED = ("ready-to-publish", "published", "ready-for-dev")


def check(base: Path, feat: str):
    """Keep the CLI's (path, findings, parsed) contract without writing files."""
    findings = []
    story = base / "02-drafts" / f"{feat}.story.md"
    tasks_path = base / "03-plan" / f"{feat}.tasks.md"
    if not story.is_file():
        return None, [f"{feat}: story draft not found"], None
    text = story.read_text(encoding="utf-8")
    parsed = frontmatter.parse(text)
    if parsed.error or not parsed.fm:
        return None, [f"{feat}: invalid story front matter"], None
    status = str(parsed.fm.get("status", "unknown"))
    if status not in APPROVED:
        findings.append(f"{feat}: status is {status}; review it with sw-review before planning")
    # Imports are local to avoid a dependency cycle with the board evaluator.
    from kitlib.lifecycle import approval_state

    if approval_state(base, feat, text) != "fresh":
        findings.append(f"{feat}: active approval is absent, stale or invalidated")
    if not tasks_path.is_file():
        return tasks_path, [*findings, f"{feat}: no tasks file at 03-plan/{feat}.tasks.md"], None
    tp = frontmatter.parse(tasks_path.read_text(encoding="utf-8"))
    if tp.error or not tp.fm:
        return tasks_path, [*findings, f"tasks file front matter: {tp.error or 'missing'}"], None
    if tp.fm.get("feat") not in (feat, f"{parsed.fm.get('scope')}:{feat}"):
        findings.append("tasks file belongs to another feature")
    if tp.fm.get("spec_hash") != hashing.draft_hash(text):
        findings.append("tasks are stale: spec_hash differs from the current story")
    section = markdown.sections(parsed.body).get("Acceptance criteria")
    acs = set(markdown.ac_blocks(section))
    blocks = markdown.task_blocks(tp.body)
    removed = set(markdown.task_tombstones(tp.body))
    if not acs:
        findings.append("story has no active acceptance criteria")
    if not blocks:
        findings.append("tasks file has no active tasks")
    covered = set()
    for tid, block in blocks.items():
        refs = ids.find_refs(block.field_line("Traces to"))
        if not refs:
            findings.append(f"{tid}: Traces to is empty")
        for ref in refs:
            if ref.id.startswith("AC-"):
                covered.add(ref.id)
                if ref.id not in acs or (ref.scope and ref.scope != parsed.fm.get("scope")):
                    findings.append(f"{tid}: traces to {ref}, which is not an active criterion")
        if not block.field_line("Done when"):
            findings.append(f"{tid}: Done when is empty")
    for ac in sorted(acs - covered):
        findings.append(f"{ac}: no task covers this criterion")
    number = ids.feat_number(feat)
    for tid in [*blocks, *removed]:
        parsed_id = ids.parse_task(tid)
        if parsed_id is None or parsed_id[0] != number:
            findings.append(f"{tid}: task number does not belong to {feat}")
    return tasks_path, findings, tp


def planning(base: Path, feat: str) -> dict:
    """A plan is deliverable only when both artifacts and current coverage exist."""
    _, findings, _ = check(base, feat)
    path = base / "03-plan" / f"{feat}.plan.md"
    if not path.is_file() or not frontmatter.parse(path.read_text(encoding="utf-8")).body.strip():
        findings.append(f"{feat}: implementation plan is missing or empty")
    return {"passing": not findings, "findings": findings}
