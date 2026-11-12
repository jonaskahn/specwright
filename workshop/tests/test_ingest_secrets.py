"""Check secret detection, PII warnings and non-disclosing CLI failure paths."""

import contextlib
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "skills/sw-ingest/scripts/secrets_scan.py"
spec = importlib.util.spec_from_file_location("ingest_secret_tests", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class IngestSecretsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "source.txt"

    def cli(self, content, *args):
        self.path.write_text(content)
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = mod.main([str(self.path), *map(str, args)])
        return code, stdout.getvalue(), stderr.getvalue()

    def test_each_secret_and_redaction(self):
        examples = {
            "atlassian-token": "ATATT" + "a" * 24,
            "aws-key": "AKIA" + "A" * 16,
            "jwt": "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.signature",
            "pem-key": "-----BEGIN RSA PRIVATE KEY-----\nprivate\n-----END RSA PRIVATE KEY-----",
            "password": "password = 'not for disclosure'",
        }
        for kind, value in examples.items():
            with self.subTest(kind=kind):
                code, output, stderr = self.cli("header\n" + value, "--redact")
                self.assertEqual(code, 0)  # the redacted copy scans clean
                report = json.loads(output)["findings"]
                self.assertEqual(report[0]["type"], kind)
                self.assertEqual(report[0]["line"], 2)
                self.assertNotIn(value, output + stderr)
                self.assertEqual(report[0]["masked_tail"], "****")
                self.assertIn("[REDACTED:" + kind + "]", self.path.read_text())
                self.assertFalse(mod.scan(self.path.read_text()))

    def test_pii_warns_and_luhn_rejects_invalid(self):
        text = "owner@example.test\n+84 912 345 678\n012345678901\n4111 1111 1111 1111"
        code, output, _ = self.cli(text)
        self.assertEqual(code, 0)
        types = {f["type"] for f in json.loads(output)["findings"]}
        self.assertTrue({"email", "vn-mobile", "cccd", "card"}.issubset(types))
        self.assertTrue(mod.luhn("4111 1111 1111 1111"))
        self.assertFalse(mod.luhn("4111 1111 1111 1112"))
        self.assertFalse(mod.luhn("0000000000000000"))
        self.assertFalse(mod.scan("No sensitive content in this policy. 4111111111111112"))

    def test_overlap_redaction_and_safe_output(self):
        text = "password='owner@example.test'"
        code, _, _ = self.cli(text, "--redact")
        self.assertEqual(code, 0)
        self.assertEqual(self.path.read_text(), "[REDACTED:password]")
        raw = self.path.parent / "raw" / "source.txt"
        raw.parent.mkdir()
        self.assertEqual(self.cli(text, "--redact", "--out", raw)[0], 2)
        self.assertFalse(raw.exists())
        out = self.path.parent / "redacted.txt"
        self.assertEqual(self.cli(text, "--redact", "--out", out)[0], 0)
        self.assertEqual(self.path.read_text(), text)
        self.assertEqual(out.read_text(), "[REDACTED:password]")

    def test_without_redact_a_secret_still_exits_one(self):
        code, output, _ = self.cli("password = 'sample-value'")
        self.assertEqual(code, 1)
        self.assertFalse(json.loads(output)["clean"])

    def test_redacting_reports_the_original_hash_and_marker_count(self):
        code, output, _ = self.cli("a password: x1y2z3\nand owner@example.test", "--redact")
        report = json.loads(output)
        self.assertEqual((code, report["redaction_markers"], report["clean"]), (0, 2, True))
        self.assertRegex(report["source_sha256"], r"^[0-9a-f]{64}$")

    def test_plain_hashes_are_not_personal_data(self):
        self.assertEqual(mod.scan("hash 123456789012abcdef0123456789abcd end"), [])
        self.assertEqual(
            mod.scan("sha256:" + "0123456789" * 6 + "abcd"),
            [],
        )
        self.assertEqual([f["type"] for f in mod.scan("id 012345678901 end")], ["cccd"])

    def test_front_matter_pii_is_skipped_but_secrets_never_are(self):
        text = (
            "---\nid: SRC-0001\nowner: o@example.test\npassword: hunter2x\n---\n"
            "Call 012345678901.\n"
        )
        found = mod.scan(text)
        self.assertEqual(sorted(f["type"] for f in found), ["cccd", "password"])

    def test_documented_examples_need_a_named_review_and_never_cover_secrets(self):
        from kitlib import hashing, scanlog

        text = "Sample owner@example.test appears in the policy.\npassword = 'sample-one'\n"
        self.path.write_text(text)
        digest = hashing.bytes_hash(self.path.read_bytes())
        log = self.path.parent / "scan-decisions.tsv"
        with self.assertRaises(ValueError):
            scanlog.append(
                log, {"source_hash": digest, "line": 1, "type": "email", "decision": "example"}
            )
        for kind, line in (("email", 1), ("password", 2)):
            scanlog.append(
                log,
                {
                    "source_hash": digest,
                    "line": line,
                    "type": kind,
                    "decision": "example",
                    "by": "PO | Lan",
                    "ref": "https://e.test/review/1",
                    "date": "2026-11-12",
                },
            )
        code, output, _ = self.cli(text, "--decisions", log)
        kinds = [f["type"] for f in json.loads(output)["findings"]]
        self.assertEqual((code, kinds), (1, ["password"]))
        scanlog.append(
            log,
            {
                "source_hash": "f" * 64,
                "line": 1,
                "type": "email",
                "decision": "example",
                "by": "PO | Lan",
                "ref": "r",
                "date": "d",
            },
        )
        self.assertEqual(len(scanlog.read(log)), 3)
        self.assertEqual(
            scanlog.allowed(scanlog.read(log), digest), {(1, "email"), (2, "password")}
        )

    def test_io_failures_and_help(self):
        with patch.object(mod.fsio, "atomic_write", side_effect=OSError("no space")):
            self.assertEqual(self.cli("password=abc", "--redact")[0], 2)
        self.path.write_bytes(b"\xff")
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(mod.main([str(self.path)]), 2)
            self.assertEqual(mod.main([str(self.path.parent / "missing")]), 2)
        for args, expected in [(["--help"], 0), ([str(self.path), "--out", "x"], 2)]:
            result = subprocess.run(
                [sys.executable, str(SCRIPT), *args], capture_output=True, timeout=10
            )
            self.assertEqual(result.returncode, expected)


if __name__ == "__main__":
    unittest.main()
