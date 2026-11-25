#!/usr/bin/env python3
"""Finish a station in one command: graph, lint gate, stack and style checks, task prompts,
data export, git checkpoint, then the hand-off decision.

    finish.py --skill sw-spec --subject "FEAT-004 story" [--cwd <project>] [--scope S]
              [--item FEAT-004]... [--until review] [--repaired] [--no-checkpoint]

Prints one JSON object. Read `handoff.mode` and act on it (handoff.md). When `lint.blocked` is
true and `repair` is set, fix the findings once and rerun with --repaired; a second blocked
lint turns the hand-off into a stop. Style findings are warnings.

Exit codes: 0 finished (read the JSON), 2 usage or a step could not run.
"""

import sys
from pathlib import Path

_here = Path(__file__).resolve().parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))

import argparse  # noqa: E402
import json  # noqa: E402
import subprocess  # noqa: E402

from kitlib import workspace  # noqa: E402

CONF = {
    "sw-start": {"gate": "draft", "data": ["scopes"], "status": True, "style": []},
    "sw-ingest": {"gate": "draft", "data": ["sources"], "style": []},
    "sw-analyze": {"gate": "draft", "data": [], "style": ["01-analysis/as-is/"], "analyze": True},
    "sw-shape": {"gate": "draft", "data": [], "style": ["01-analysis/"]},
    "sw-spec": {"gate": "review", "data": ["registry"], "style": ["02-drafts/"]},
    "sw-review": {"gate": "review", "data": ["quality"], "style": []},
    "sw-plan": {"gate": "review", "data": ["tasks"], "style": ["03-plan/"], "plan": True},
    "sw-publish": {"gate": "publish", "data": ["registry", "quality"], "style": []},
}
LINT_BLOCKED = {10, 20, 30}


def _run(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, *args], cwd=cwd, capture_output=True, text=True, check=False
    )


def _tail(text: str, n: int = 8) -> list[str]:
    return [ln for ln in (text or "").strip().splitlines() if ln.strip()][-n:]


def _skill_scripts(skill: str) -> Path | None:
    """The calling skill's own scripts/ folder, in an install or a source checkout."""
    top = _here.parent.parent
    for cand in (top / "scripts", top / skill / "scripts"):
        if (cand.parent / "SKILL.md").is_file() and cand.parent.name == skill:
            return cand
    return None


def _changed(base: Path, prefixes: list[str]) -> list[Path]:
    """Uncommitted Markdown files of the station's folders (git), else none."""
    done = subprocess.run(
        ["git", "-C", str(base), "status", "--porcelain", "--untracked-files=all", "."],
        capture_output=True,
        text=True,
        check=False,
    )
    if done.returncode != 0:
        return []
    top = subprocess.run(
        ["git", "-C", str(base), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()
    out = []
    for line in done.stdout.splitlines():
        rel = line[3:].strip().strip('"')
        path = (Path(top) / rel).resolve()
        try:
            inner = path.relative_to(base.resolve()).as_posix()
        except ValueError:
            continue
        if (
            path.suffix == ".md"
            and path.is_file()
            and any(inner.startswith(p) for p in prefixes)
            and "/prompts/" not in inner
        ):
            out.append(path)
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill", required=True, choices=sorted(CONF))
    parser.add_argument("--subject", required=True)
    parser.add_argument("--cwd", default=".")
    parser.add_argument("--scope")
    parser.add_argument("--item", action="append", default=[])
    parser.add_argument("--until", choices=["shape", "spec", "review", "plan", "publish"])
    parser.add_argument("--repaired", action="store_true", help="the one repair pass is done")
    parser.add_argument("--no-checkpoint", action="store_true")
    a = parser.parse_args(argv)
    conf = CONF[a.skill]
    try:
        cwd = Path(a.cwd).resolve()
        root = workspace.find_root(cwd)
        if root is None:
            raise ValueError("no workspace; run sw-start")
        scope = workspace.resolve(root, a.scope, a.item[0] if a.item else None, cwd, False)
        base = workspace.scope_dir(root, scope)
    except workspace.AskUser as exc:
        print(f"{exc} options: {exc.options}", file=sys.stderr)
        return 2
    except (ValueError, OSError, workspace.WorkspaceError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    sc = ["--scope", scope]
    s = str(_here)
    report: dict = {"skill": a.skill, "scope": scope, "steps": []}

    def step(name: str, done: subprocess.CompletedProcess, ok_codes=(0,)) -> bool:
        ok = done.returncode in ok_codes
        report["steps"].append(
            {
                "step": name,
                "ok": ok,
                "code": done.returncode,
                "out": _tail(done.stdout + done.stderr),
            }
        )
        return ok

    step("graph", _run([f"{s}/graph.py", "build", "--cwd", str(base), *sc], base))

    # Plan: stack check and agent prompts per feature with a tasks file.
    if conf.get("plan"):
        feats = [i.split(":")[-1] for i in a.item] or sorted(
            p.name.split(".")[0] for p in (base / "03-plan").glob("FEAT-*.tasks.md")
        )
        scripts = _skill_scripts(a.skill)
        report["stack"], report["prompts"] = {}, {}
        for feat in feats:
            done = _run([f"{s}/stack.py", "check", "--feat", feat, "--cwd", str(base), *sc], base)
            try:
                report["stack"][feat] = json.loads(done.stdout).get("findings", [])
            except ValueError:
                report["stack"][feat] = _tail(done.stderr) or ["stack check failed"]
            if scripts and (scripts / "task_prompts.py").is_file():
                done = _run(
                    [str(scripts / "task_prompts.py"), "--feat", feat, "--cwd", str(base), *sc],
                    base,
                )
                report["prompts"][feat] = (
                    _tail(done.stdout, 3) if done.returncode == 0 else _tail(done.stderr, 2)
                )
        if any(report["prompts"].values()):
            _run([f"{s}/graph.py", "build", "--cwd", str(base), *sc], base)

    if (_here / "sw_lint.py").is_file():
        lint = _run(
            [
                f"{s}/sw_lint.py",
                "--root",
                str(base),
                "--gate",
                conf["gate"],
                *sc,
                "--format",
                "text",
            ],
            base,
        )
    else:  # a skill that ships no lint (sw-ingest): nothing to gate here
        lint = subprocess.CompletedProcess([], 0, "lint not shipped with this skill; skipped", "")
    blocked = lint.returncode in LINT_BLOCKED
    report["lint"] = {
        "gate": conf["gate"],
        "code": lint.returncode,
        "blocked": blocked,
        "out": _tail(lint.stdout, 12),
    }
    if lint.returncode not in (0, *LINT_BLOCKED):
        report["lint"]["error"] = _tail(lint.stderr, 4)

    if conf["style"]:
        files = _changed(base, conf["style"])
        if files:
            done = _run([f"{s}/style_check.py", *map(str, files), "--format", "json"], base)
            try:
                report["style"] = json.loads(done.stdout)["findings"]
            except (ValueError, KeyError):
                report["style"] = _tail(done.stderr)
        else:
            report["style"] = []

    if conf.get("status") and (_here / "status.py").is_file():
        step("status", _run([f"{s}/status.py", "--cwd", str(base), *sc, "--save"], base))
    for kind in conf["data"]:
        step(
            f"data {kind}",
            _run([f"{s}/data.py", "export", kind, "--as", a.skill, "--cwd", str(base), *sc], base),
        )

    if not a.no_checkpoint:
        cp = _run(
            [
                f"{s}/checkpoint.py",
                "commit",
                "--skill",
                a.skill,
                "--subject",
                a.subject,
                "--cwd",
                str(base),
                *sc,
            ],
            base,
        )
        report["checkpoint"] = _tail(cp.stdout + cp.stderr, 2)

    # sw-analyze: the gap table, not the board, decides what comes next.
    if conf.get("analyze"):
        scripts = _skill_scripts(a.skill)
        results = {}
        for item in a.item:
            done = _run([str(scripts / "analyze.py"), "check", item, "--cwd", str(base), *sc], base)
            try:
                results[item] = json.loads(done.stdout)
            except ValueError:
                results[item] = {"findings": _tail(done.stderr, 2) or ["check failed"], "ask": []}
        report["analysis"] = results
        findings = [f"{i}: {f}" for i, r in results.items() for f in r.get("findings", [])]
        asks = [{"item": i, **q} for i, r in results.items() for q in r.get("ask", [])]
        if not a.item:
            handoff = {"mode": "stop", "reason": "choose a candidate to analyse (inventory.md)"}
        elif findings and not a.repaired:
            handoff = {"mode": "repair", "reason": "; ".join(findings[:4])}
        elif findings:
            handoff = {
                "mode": "stop",
                "reason": "analysis still invalid: " + "; ".join(findings[:3]),
            }
        elif asks:
            handoff = {
                "mode": "stop",
                "reason": "confirm these rows (low confidence, divergent, unknown or partial)",
                "waiting": asks,
            }
        else:
            handoff = {
                "mode": "continue",
                "next_skill": "sw-spec",
                "items": a.item,
                "reason": "; ".join(f"{i}: {r['recommend']}" for i, r in results.items()),
            }
        handoff["say"] = (
            f"→ sw-spec for {', '.join(a.item)}"
            if handoff["mode"] == "continue"
            else "Paused: " + handoff["reason"]
        )
        report["handoff"] = handoff
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0

    cmd = [f"{s}/handoff.py", "next", "--cwd", str(base), *sc, "--done", a.skill]
    if len(a.item) == 1:
        cmd += ["--item", a.item[0]]
    if a.until:
        cmd += ["--until", a.until]
    done = _run(cmd, base)
    try:
        handoff = json.loads(done.stdout)
    except ValueError:
        handoff = {"mode": "stop", "reason": "hand-off failed: " + " ".join(_tail(done.stderr, 2))}
    if blocked and not a.repaired:
        report["repair"] = "fix the lint findings once, then rerun finish.py with --repaired"
        handoff = {**handoff, "mode": "repair", "say": "Repairing lint findings (one pass)."}
    elif blocked:
        handoff = {
            **handoff,
            "mode": "stop",
            "reason": f"{conf['gate']} lint still blocked after one repair pass",
            "say": f"Paused: {conf['gate']} lint still blocked after one repair pass.",
        }
    advisory = ("no stack profile", "stack profile is not locked")
    stack_findings = [
        f for v in (report.get("stack") or {}).values() for f in v if not f.startswith(advisory)
    ]
    if stack_findings and handoff.get("mode") == "done":
        handoff = {
            **handoff,
            "mode": "stop",
            "reason": "tasks break the stack profile: " + "; ".join(stack_findings[:3]),
            "say": "Paused: tasks break the stack profile.",
        }
    report["handoff"] = handoff
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
