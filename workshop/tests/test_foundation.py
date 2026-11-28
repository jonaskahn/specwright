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
    def test_rust_tooling_and_coverage_gate(self):
        profile = {"layers": {"backend": {"language": "Rust"}}}
        self.assertEqual(foundation.language_of(profile, "backend"), "rust")
        self.assertIn("cargo", foundation.questions(profile)[0]["options"][0])
        tooling = foundation.default_tooling(profile)
        self.assertEqual(tooling["layers"]["backend"]["build"], "cargo")
        self.assertEqual(tooling["layers"]["backend"]["format"], "rustfmt")
        self.assertEqual(tooling["layers"]["backend"]["lint"], "clippy")
        tooling["coverage"] = 85
        cmds = foundation.commands(tooling)["backend"]
        self.assertIn("cargo test --workspace --locked", cmds["test"])
        self.assertIn("--fail-under-lines 85", cmds["test"])
        self.assertNotIn("{coverage}", cmds["test"])
        mk = foundation.makefile(tooling, "Desktop")
        self.assertIn("cargo fmt --all -- --check", mk)
        self.assertIn("cargo clippy", mk)
        self.assertIn("cargo check", mk)
        self.assertIn("--fail-under-lines 85", mk)
        self.assertIn("Cargo.toml", foundation.agents_md(tooling, "Desktop", {}))

    def test_popular_language_presets_and_aliases(self):
        cases = {
            "C": ("c", "cmake"),
            "C++": ("c", "cmake"),
            "PHP": ("php", "composer"),
            "Ruby": ("ruby", "bundler"),
            "Swift": ("swift", "swiftpm"),
            "Kotlin": ("kotlin", "gradle"),
            "JS": ("javascript", "npm"),
            "TS": ("typescript", "pnpm"),
            "C#": ("csharp", "dotnet"),
            "golang": ("go", "go"),
        }
        for language, (canonical, build) in cases.items():
            with self.subTest(language=language):
                profile = {"layers": {"backend": {"language": language}}}
                self.assertEqual(foundation.language_of(profile, "backend"), canonical)
                tooling = foundation.default_tooling(profile)
                self.assertEqual(tooling["layers"]["backend"]["build"], build)
                self.assertLessEqual(len(foundation.questions(profile)), 5)
                cmds = foundation.commands(tooling)["backend"]
                for target in ("setup", "fmt", "fmt-check", "lint", "test", "build"):
                    self.assertTrue(cmds[target])
                self.assertNotIn("{coverage}", foundation.makefile(tooling, "Demo"))

    def test_javascript_does_not_require_typescript(self):
        for build in ("npm", "pnpm"):
            profile = {"layers": {"frontend": {"language": "javascript", "build": build}}}
            cmds = foundation.commands(foundation.default_tooling(profile))["frontend"]
            self.assertNotIn("typecheck", cmds)
            self.assertNotIn("tsc", " ".join(cmds.values()))

    def test_swift_coverage_fails_closed_until_configured(self):
        profile = {"layers": {"mobile": {"language": "swift"}}}
        mk = foundation.makefile(foundation.default_tooling(profile), "Demo")
        self.assertIn("coverage-check:", mk)
        self.assertIn("\t@exit 1", mk)

    def test_c_coverage_uses_selected_floor(self):
        tooling = foundation.default_tooling({"layers": {"backend": {"language": "C++"}}})
        tooling["coverage"] = 90
        test = foundation.commands(tooling)["backend"]["test"]
        self.assertIn("--fail-under-line 90", test)
        self.assertIn("cmake --preset coverage", test)

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
        for heading in (
            "## 1. Think before coding",
            "## 2. Simplicity first",
            "## 3. Surgical changes",
            "## 4. Goal-driven execution",
            "## Coding conventions",
            "`make lint`",
            ".specwright/index.md",
        ):
            self.assertIn(heading, locked)
        self.assertNotIn("## Documentary proof", locked)
        self.assertNotIn("Don't assume. Don't hide confusion.", locked)

    def test_clean_code_rules_are_per_language_and_nested_files_hold_only_the_difference(self):
        t = foundation.default_tooling(PROFILE)
        root = foundation.agents_md(t, "Demo", {})
        self.assertIn("## Coding conventions", root)
        self.assertIn("Per-language rules live in each layer", root)
        self.assertNotIn("Constructor injection", root)
        backend = foundation.layer_agents_md(t, "backend")
        self.assertIn("Constructor injection", backend)
        self.assertIn("Root AGENTS.md rules apply", backend)
        self.assertNotIn("Think first", backend)
        self.assertNotIn(".specwright/index.md", backend)
        single = foundation.default_tooling({"layers": {"backend": {"language": "python"}}})
        self.assertIn("bare except", foundation.agents_md(single, "Demo", {}))
        for lang in foundation.CATALOG:
            if "alias" not in foundation.CATALOG[lang]:
                self.assertTrue(foundation.clean_code(lang), lang)

    def test_existing_setup_names_what_the_folder_has(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "Makefile").write_text("all:\n")
            (folder / "tests").mkdir()
            found = foundation.existing_setup(folder)
        self.assertEqual(found["gate"], ["Makefile"])
        self.assertEqual(found["tests"], ["tests"])
        self.assertEqual(found["lint"], [])

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
