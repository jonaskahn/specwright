"""Read-only task coverage and planning checks shared by board, CLI and publish."""

from pathlib import Path

from kitlib import frontmatter, hashing, ids, markdown, paths, rtm, schema, workspace

APPROVED = ("ready-to-publish", "published", "ready-for-dev", "in-development", "done")


def asset_rows(base: Path) -> dict[str, tuple[str, str]]:
    """ASSET id to (kind, refs) from the scope's asset registry; empty when there is none."""
    path = base / ".metadata/asset-registry.md"
    if not path.is_file():
        return {}
    try:
        doc = rtm.read_table(path, list(schema.ASSET_REGISTRY_COLUMNS))
    except (OSError, ValueError):
        return {}
    kind, refs = doc.table.col("Kind"), doc.table.col("Refs")
    return {row[0].split(":")[-1]: (row[kind] or "other", row[refs]) for row in doc.table.rows}


def asset_kinds(base: Path) -> dict[str, str]:
    """ASSET id to kind."""
    return {key: kind for key, (kind, _) in asset_rows(base).items()}


def _visual_findings(base: Path, tid: str, block, layer: str | None, story_visuals: set[str]):
    """A task's Visuals must name registered assets or existing diagrams; UI tasks must cite one."""
    text = block.field_line("Visuals")
    cited = [r.id for r in ids.find_refs(text) if r.id.startswith("ASSET-")]
    diagrams = [
        p.rstrip(".,;") for p in text.replace(",", " ").split() if p.startswith("diagrams/")
    ]
    kinds = asset_kinds(base)
    out = [
        f"{tid}: Visuals names {a}, which is not in the asset registry"
        for a in cited
        if a not in kinds
    ]
    out += [
        f"{tid}: Visuals names {p}, which does not exist"
        for p in diagrams
        if not (base / p).is_file()
    ]
    if layer in schema.UI_TASK_LAYERS and story_visuals and not (cited or diagrams):
        out.append(
            f"{tid}: a {layer} task needs Visuals: cite the mockup or diagram it builds "
            f"({', '.join(sorted(story_visuals))})"
        )
    return out


def workspace_root(base: Path):
    """The spec root that holds base, or None when base is not inside a workspace."""
    try:
        return workspace.find_root(base)
    except workspace.AskUser:
        return None


def _touch_paths(block) -> list[str]:
    return [
        item.strip()
        for item in block.field_line("Touches").split(",")
        if item.strip() and item.strip().lower() not in ("none", "unknown")
    ]


def _dep_ids(block) -> set[str]:
    raw = block.field_line("Depends on").strip()
    if not raw or raw.lower() == "none":
        return set()
    return {part.strip() for part in raw.replace(",", " ").split() if part.startswith("TASK-")}


def overlap_findings(blocks) -> list[str]:
    """Two tasks that write the same path must name each other in Depends on."""
    items = [(tid, _touch_paths(block)) for tid, block in blocks.items()]
    found = []
    for index, (tid, touched) in enumerate(items):
        for other, other_paths in items[index + 1 :]:
            if not set(touched) & set(other_paths):
                continue
            if other not in _dep_ids(blocks[tid]) and tid not in _dep_ids(blocks[other]):
                found.append(
                    f"{tid} and {other} touch the same path and neither Depends on the other"
                )
    return found


def new_path_findings(root: Path, scope: str, blocks) -> list[str]:
    """`new:<path>` is legal only when a code root is registered and the parent directory exists."""
    from kitlib import coderoots

    try:
        registered = coderoots.registered(root, scope)
        folder = workspace.code_root(root, scope)
        repo = workspace.code_repo_root(root)
    except (workspace.WorkspaceError, workspace.AskUser):
        registered, folder, repo = [], None, None
    found = []
    for tid, block in blocks.items():
        for item in _touch_paths(block):
            if not item.startswith("new:"):
                continue
            parent = Path(item[4:]).parent.as_posix()
            if parent in ("", "."):
                parent = item[4:]
            ok = bool(registered) and folder is not None and repo is not None
            if ok:
                try:
                    target = workspace.safe_join(repo, parent)
                    ok = target.is_dir() and (target == folder or folder in target.parents)
                except workspace.WorkspaceError:
                    ok = False
            if not ok:
                found.append(
                    f"{tid}: Touches {item} needs a registered code root and an existing parent"
                )
    return found


def check(base: Path, feat: str):
    """Keep the CLI's (path, findings, parsed) contract without writing files."""
    findings = []
    story = paths.story(base, feat)
    tasks_path = paths.tasks_file(base, feat)
    if not story.is_file():
        return None, [f"{feat}: story draft not found"], None
    text = story.read_text(encoding="utf-8")
    parsed = frontmatter.parse(text)
    if parsed.error or not parsed.fm:
        return None, [f"{feat}: invalid story front matter"], None
    status = str(parsed.fm.get("status", "unknown"))
    if status not in APPROVED:
        findings.append(f"{feat}: status is {status}; the review step in sw-craft finalizes it")
    # Imports are local to avoid a dependency cycle with the board evaluator.
    from kitlib.lifecycle import approval_state

    if approval_state(base, feat, text) != "fresh":
        findings.append(f"{feat}: active approval is absent, stale or invalidated")
    if not tasks_path.is_file():
        missing = f"{feat}: no tasks file at tasks/{feat}/{feat}.tasks.md"
        return tasks_path, [*findings, missing], None
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
    kinds = asset_kinds(base)
    listed = {str(a) for a in parsed.fm.get("assets") or []}
    story_visuals = {a for a in listed if kinds.get(a) in schema.VISUAL_ASSET_KINDS}
    for tid, block in blocks.items():
        layer = markdown.task_layer(block.title)
        if layer is None:
            findings.append(
                f"{tid}: title needs a layer prefix, one of [{'], ['.join(schema.TASK_LAYERS)}]"
            )
        elif layer not in schema.TASK_LAYERS:
            findings.append(
                f"{tid}: unknown layer [{layer}]; use one of {', '.join(schema.TASK_LAYERS)}"
            )
        findings += _visual_findings(base, tid, block, layer, story_visuals)
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
        if markdown.task_progress(block) == "done" and not block.field_line("Evidence"):
            findings.append(f"{tid}: done needs an Evidence line (how it was proven)")
    for ac in sorted(acs - covered):
        findings.append(f"{ac}: no task covers this criterion")
    number = ids.feat_number(feat)
    for tid in [*blocks, *removed]:
        parsed_id = ids.parse_task(tid)
        if parsed_id is None or parsed_id[0] != number:
            findings.append(f"{tid}: task number does not belong to {feat}")
    findings += overlap_findings(blocks)
    root = workspace_root(base)
    if root is not None:
        findings += new_path_findings(root, str(parsed.fm.get("scope") or ""), blocks)
    return tasks_path, findings, tp


def planning(base: Path, feat: str) -> dict:
    """A plan is deliverable only when both artifacts and current coverage exist."""
    _, findings, _ = check(base, feat)
    path = paths.plan_file(base, feat)
    if not path.is_file() or not frontmatter.parse(path.read_text(encoding="utf-8")).body.strip():
        findings.append(f"{feat}: implementation plan is missing or empty")
    return {"passing": not findings, "findings": findings}


PLAN_SECTIONS = (
    "Approach",
    "Visual references",
    "Constraints",
    "Dependencies",
    "Evidence from the codebase",
    "Open Dev questions",
)
PLAN_TASK_FIELDS = ("Files", "Change", "Test", "DoD", "Accepts", "Coverage")


def task_sections(body: str) -> dict[str, markdown.Section]:
    """Plan sections by task ID: `### TASK-001-1 — [backend] title` is keyed `TASK-001-1`."""
    out: dict[str, markdown.Section] = {}
    for section in markdown.iter_sections(body, level=3):
        key = section.name.split()[0] if section.name else ""
        out.setdefault(key, section)
    return out


def plan_findings(base: Path, feat: str) -> list[str]:
    """Every active task needs a detailed plan section; a gone task's section is stale."""
    path = paths.plan_file(base, feat)
    parsed = frontmatter.parse(path.read_text(encoding="utf-8"))
    if parsed.error:
        return [f"{feat}: plan front matter: {parsed.error}"]
    found = markdown.sections(parsed.body)
    out = [
        f"{feat}: plan section '{name}' is missing" for name in PLAN_SECTIONS if name not in found
    ]
    sections = task_sections(parsed.body)
    tasks_path = paths.tasks_file(base, feat)
    blocks = {}
    if tasks_path.is_file():
        blocks = markdown.task_blocks(
            frontmatter.parse(tasks_path.read_text(encoding="utf-8")).body
        )
    for tid in sorted(blocks):
        section = sections.get(tid)
        if section is None:
            out.append(f"{tid}: plan section is missing")
            continue
        for field in PLAN_TASK_FIELDS:
            if not any(line.strip().startswith(f"{field}:") for _, line in section.lines):
                out.append(f"{tid}: plan section has no {field}: line")
    for name in sorted(set(sections) - set(blocks)):
        if name.startswith("TASK-"):
            out.append(f"{name}: plan section names no active task")
    listed = {str(t) for t in parsed.fm.get("tasks") or []}
    if listed != set(blocks):
        missing = ", ".join(sorted(set(blocks) ^ listed))
        out.append(f"{feat}: plan front matter `tasks` must list every active task ({missing})")
    return out


def label(base: Path, feat: str) -> str:
    """`FEAT-001 — Request a refund (LEG-100)`: the ID with the names a reader knows it by."""
    story = paths.story(base, feat)
    fm = (frontmatter.parse(story.read_text(encoding="utf-8")).fm or {}) if story.is_file() else {}
    name = str(fm.get("title") or fm.get("jira_summary") or "")
    aliases = [str(a) for a in fm.get("aliases") or []]
    text = f"{feat} — {name}" if name else feat
    return text + (f" ({', '.join(aliases)})" if aliases else "")
