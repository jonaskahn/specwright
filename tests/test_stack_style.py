"""Stack profile (detect, lock, task check) and agent-style checks. No workspace needed."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "_shared" / "scripts"))

import style_check  # noqa: E402

from kitlib import markdown, stack  # noqa: E402


class Detect(unittest.TestCase):
    def test_spring_react_compose(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "api").mkdir()
            (root / "api/pom.xml").write_text(
                "<project><parent><artifactId>spring-boot-starter-parent</artifactId>"
                "\n<version>3.3.4</version></parent>\n<java.version>21</java.version></project>"
            )
            (root / "package.json").write_text(
                json.dumps({"dependencies": {"react": "^19.0.0"}, "scripts": {"test": "x"}})
            )
            (root / "compose.yml").write_text("services:\n  db:\n    image: postgres:16\n")
            found = stack.detect(root)
            self.assertEqual(found["backend"]["framework"], "spring-boot")
            self.assertEqual(found["backend"]["version"], "21")
            self.assertEqual(found["frontend"]["framework"], "react")
            self.assertIn("postgres", found["data"]["framework"])


class Lock(unittest.TestCase):
    def profile(self):
        data = stack.empty()
        data["layers"] = {"backend": {"language": "java", "framework": "spring-boot"}}
        return data

    def test_lock_needs_the_shown_hash(self):
        data = self.profile()
        preview = stack.lock(data, None)
        with self.assertRaises(stack.StackError):
            stack.lock(data, "sha256:000000000000")
        self.assertTrue(stack.lock(data, preview["hash"])["applied"])
        self.assertEqual(data["status"], "locked")

    def test_locked_change_needs_reason_and_unlocks(self):
        data = self.profile()
        stack.lock(data, stack.lock(data, None)["hash"])
        with self.assertRaises(stack.StackError):
            stack.set_value(data, "backend.version", "21", None)
        stack.set_value(data, "backend.version", "21", "upgrade")
        self.assertEqual(data["status"], "proposed")


class CheckTasks(unittest.TestCase):
    def test_stray_and_forbidden_technology(self):
        data = stack.empty()
        data["status"] = "locked"
        data["layers"] = {"backend": {"language": "java", "framework": "spring-boot"}}
        data["libraries"]["forbidden"] = ["lombok"]
        body = (
            "### TASK-001-1 — [backend] Save request\nTraces to: AC-001-1\n"
            "Stack: java 21 · spring-boot 3.3\nDone when: uses Django and lombok\n"
            "### TASK-001-2 — [backend] Go back to list\nTraces to: AC-001-2\n"
            "Done when: go to the list\n"
        )
        findings = stack.check_tasks(data, markdown.task_blocks(body), markdown.task_layer)
        text = " ".join(findings)
        self.assertIn("django", text)
        self.assertIn("lombok", text)
        self.assertIn("TASK-001-2: Stack line missing", text)
        self.assertNotIn("names go", text)  # "go" as a verb is not the language


class Style(unittest.TestCase):
    def test_flags_hedge_and_vague_but_not_quotes_or_measured_lines(self):
        text = (
            "---\nid: x\n---\nIt should probably be fast.\n"
            'Responds in 2 s, fast.\nShow "Please retry".\n'
        )
        found = style_check.check_text(text, "f.md")
        words = {(f["line"], f["word"]) for f in found}
        self.assertIn((4, "should probably"), words)
        self.assertIn((4, "fast"), words)
        self.assertNotIn((5, "fast"), words)
        self.assertFalse(any(f["line"] == 6 for f in found))


if __name__ == "__main__":
    unittest.main()
