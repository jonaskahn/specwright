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

ROOT = Path(__file__).resolve().parents[1]
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
                self.assertEqual(code, 1)
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
        self.assertEqual(code, 1)
        self.assertEqual(self.path.read_text(), "[REDACTED:password]")
        raw = self.path.parent / "raw" / "source.txt"
        raw.parent.mkdir()
        self.assertEqual(self.cli(text, "--redact", "--out", raw)[0], 2)
        self.assertFalse(raw.exists())
        out = self.path.parent / "redacted.txt"
        self.assertEqual(self.cli(text, "--redact", "--out", out)[0], 1)
        self.assertEqual(self.path.read_text(), text)
        self.assertEqual(out.read_text(), "[REDACTED:password]")

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
