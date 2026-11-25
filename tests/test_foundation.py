"""Foundation story catalog: questions, Makefile, AGENTS.md and story sections."""

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "_shared" / "scripts"))

from kitlib import foundation  # noqa: E402

PROFILE = {
    "layers": {
        "backend": {"language": "java", "framework": "spring-boot", "build": "gradle"},
        "frontend": {"language": "typescript", "framework": "react"},
        "data": {"framework": "postgres"},
    }
}


class Foundation(unittest.TestCase):
    def test_questions_prefilled_and_capped(self):
        qs = foundation.questions(PROFILE)
        self.assertLessEqual(len(qs), 5)
        self.assertTrue(qs[0]["options"][0].startswith("gradle"))
        self.assertIn("pnpm", qs[1]["options"][0])

    def test_makefile_has_gate_and_tabs(self):
        mk = foundation.makefile(foundation.default_tooling(PROFILE), "Demo")
        self.assertIn("check: fmt-check lint typecheck test", mk)
        self.assertIn("\tcd backend && ./gradlew --quiet spotlessCheck", mk)
        self.assertFalse(re.search(r"^ {2,}\S", mk, re.M), "recipes must use tabs")

    def test_agents_md_states_lock_and_credits_source(self):
        t = foundation.default_tooling(PROFILE)
        unlocked = foundation.agents_md(t, "Demo", {"backend": "java 21"})
        self.assertIn("not locked yet", unlocked)
        locked = foundation.agents_md(t, "Demo", {"backend": "java 21"}, "sha256:abc")
        self.assertIn("locked sha256:abc", locked)
        self.assertIn("andrej-karpathy-skills", locked)

    def test_story_sections(self):
        t = foundation.default_tooling(PROFILE)
        t["coverage"] = 85
        s = foundation.story_sections(t, "BO-001", "007")
        self.assertIn("BO-001", s["Goal"])
        acs = re.findall(r"### (AC-007-\d+)", s["Acceptance criteria"])
        self.assertEqual(len(acs), 8)
        self.assertIn("Example: 84.9% fails, 85.0% passes", s["Business rules"])
        t["ci"], t["ai_workflow"] = "none", "none"
        acs = re.findall(
            r"### AC-", foundation.story_sections(t, "BO-001", "007")["Acceptance criteria"]
        )
        self.assertEqual(len(acs), 6)


if __name__ == "__main__":
    unittest.main()
