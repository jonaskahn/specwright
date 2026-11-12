import tempfile
import unittest
from pathlib import Path

from kitlib import jira_mock, jira_port, jira_rest


class RestAdapterTests(unittest.TestCase):
    def port(self, mock):
        return jira_rest.JiraREST(
            site=mock.url,
            email="agent@example.test",
            token="not-a-real-token",
            timeout=3,
            allow_http=True,
        )

    def test_configuration_requires_a_plain_https_origin_by_default(self):
        with self.assertRaises(ValueError):
            jira_rest.JiraREST(site="http://example.test", email="a", token="b")
        with self.assertRaises(ValueError):
            jira_rest.JiraREST(site="https://example.test/path", email="a", token="b")
        with self.assertRaises(ValueError):
            jira_rest.JiraREST(site="https://example.test", email="", token="b")

    def test_retry_after_accepts_seconds_and_http_dates(self):
        self.assertEqual(jira_rest.retry_after("4"), 4.0)
        self.assertEqual(jira_rest.retry_after("bad"), 1.0)

    def test_create_edit_and_property_round_trip_through_http(self):
        with jira_mock.MockJira() as mock:
            port = self.port(mock)
            created = port.create_issue(
                {
                    "project": {"key": "PROJ"},
                    "labels": ["specwright", "feat:FEAT-001"],
                    "summary": "Submit a refund",
                    "updated": "t0",
                }
            )
            self.assertEqual(created["key"], "PROJ-1")
            port.set_property(created["key"], "specwright.identity", {"id": "REF:FEAT-001"})
            self.assertEqual(
                port.get_property(created["key"], "specwright.identity"),
                {"id": "REF:FEAT-001"},
            )
            issue = port.get_issue(created["key"])
            port.edit_issue(created["key"], {"summary": "Submit a refund request"})
            self.assertNotEqual(
                port.get_issue(created["key"])["fields"]["updated"], issue["fields"]["updated"]
            )
            self.assertEqual(
                port.get_issue(created["key"])["fields"]["summary"],
                "Submit a refund request",
            )

    def test_search_enumerates_all_pages_and_rejects_unbounded_jql(self):
        with jira_mock.MockJira(page_size=1) as mock:
            for number in (1, 2, 3):
                mock.seed(
                    f"PROJ-{number}",
                    {"labels": ["feat:FEAT-001"], "updated": f"t{number}"},
                )
            port = self.port(mock)
            found = port.search_by_label("PROJ", "feat:FEAT-001")
            self.assertEqual([item["key"] for item in found], ["PROJ-1", "PROJ-2", "PROJ-3"])
            with self.assertRaises(ValueError):
                port.search_jql("labels = feat:FEAT-001")
            with self.assertRaises(ValueError):
                port.search_jql('project = PROJ OR labels = "x"')

    def test_rate_limit_and_permission_errors_are_typed(self):
        with jira_mock.MockJira() as mock:
            port = self.port(mock)
            mock.inject("GET", "issue/PROJ-1", "rate-limit")
            with self.assertRaises(jira_port.RateLimited) as ctx:
                port.get_issue("PROJ-1")
            self.assertEqual(ctx.exception.retry_after, 2.0)
            mock.inject("GET", "issue/PROJ-1", "forbidden")
            with self.assertRaises(jira_port.PermissionDenied):
                port.get_issue("PROJ-1")

    def test_dropped_create_response_is_ambiguous_but_not_duplicated(self):
        with jira_mock.MockJira() as mock:
            port = self.port(mock)
            mock.inject("POST", "issue", "drop-after-create")
            with self.assertRaises(jira_port.Timeout) as ctx:
                port.create_issue({"project": {"key": "PROJ"}, "labels": ["feat:FEAT-001"]})
            self.assertTrue(ctx.exception.ambiguous)
            self.assertEqual(list(mock.issues), ["PROJ-1"])
            self.assertEqual(
                [item["key"] for item in port.search_by_label("PROJ", "feat:FEAT-001")],
                ["PROJ-1"],
            )

    def test_attachment_uses_the_required_multipart_headers(self):
        with jira_mock.MockJira() as mock, tempfile.TemporaryDirectory() as raw:
            mock.seed("PROJ-1", {"updated": "t0"})
            path = Path(raw) / "sw-diagram.html"
            path.write_text("<html>offline</html>")
            self.port(mock).attach_file("PROJ-1", path)
            self.assertEqual(len(mock.attachments), 1)
            self.assertIn(b'name="file"', mock.attachments[0]["body"])
            self.assertIn(b"offline", mock.attachments[0]["body"])

    def test_authorization_never_appears_in_diagnostics(self):
        with jira_mock.MockJira() as mock:
            port = self.port(mock)
            self.assertNotIn("not-a-real-token", repr(port.__dict__))
            self.assertNotIn("not-a-real-token", str(jira_port.PermissionDenied()))


if __name__ == "__main__":
    unittest.main()
