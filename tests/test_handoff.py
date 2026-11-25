"""Hand-off decisions between stations (kitlib.handoff). Pure logic; no workspace needed."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "_shared" / "scripts"))

from kitlib import handoff  # noqa: E402


def row(rid, station, condition, kind="feat", questions=None, blockers=None, split=False):
    r = {"id": rid, "station": station, "condition": condition, "kind": kind}
    r["blockers"] = blockers or []
    if questions:
        r["questions"] = questions
    if split:
        r["split_accepted"] = True
    return r


F1, F2, E1 = "REF:FEAT-001", "REF:FEAT-002", "REF:EPIC-001"


class AutoFlow(unittest.TestCase):
    def test_finished_spec_submits_and_continues_to_review(self):
        a = handoff.decide([row(F1, "spec", "in-progress")], done="sw-spec")
        self.assertEqual((a["mode"], a["next_skill"]), ("continue", "sw-review"))
        self.assertEqual(a["transitions"], [{"item": F1, "action": "submit-review"}])

    def test_blocking_question_waits_and_siblings_go_on(self):
        rows = [
            row(F1, "spec", "in-progress"),
            row(F2, "spec", "in-progress", questions=["Q-001 x"]),
        ]
        a = handoff.decide(rows, done="sw-spec")
        self.assertEqual(a["items"], [F1])
        self.assertEqual([w["kind"] for w in a["waiting"]], ["input"])

    def test_review_is_a_human_gate(self):
        a = handoff.decide([row(F1, "review", "in-progress")], done="sw-review")
        self.assertEqual(a["mode"], "stop")
        self.assertEqual(a["waiting"][0]["kind"], "decision")

    def test_accepted_feature_continues_to_plan(self):
        a = handoff.decide([row(F1, "plan", "blocked")])
        self.assertEqual((a["mode"], a["next_skill"]), ("continue", "sw-plan"))

    def test_work_without_questions_runs_before_gated_stations(self):
        rows = [row(F1, "review", "in-progress"), row(F2, "plan", "blocked")]
        self.assertEqual(handoff.decide(rows)["next_skill"], "sw-plan")

    def test_complete_plan_is_done_and_never_offers_publication(self):
        a = handoff.decide([row(F1, "plan", "complete")], done="sw-plan")
        self.assertEqual(a["mode"], "done")
        self.assertNotIn("publish", a["reason"].lower())

    def test_publish_station_never_continues(self):
        self.assertEqual(handoff.decide([row(F1, "publish", "in-progress")])["mode"], "stop")

    def test_failing_plan_after_run_stops(self):
        a = handoff.decide([row(F1, "plan", "blocked", blockers=["AC uncovered"])], done="sw-plan")
        self.assertEqual(a["mode"], "stop")

    def test_unknown_state_waits_without_blocking_siblings(self):
        rows = [row(F1, "spec", "unknown", blockers=["forked"]), row(F2, "spec", "not-started")]
        a = handoff.decide(rows)
        self.assertEqual((a["next_skill"], a["items"]), ("sw-spec", [F2]))
        self.assertEqual(a["waiting"][0]["kind"], "blocked")

    def test_shape_ends_at_split_acceptance(self):
        a = handoff.decide([row(E1, "shape", "in-progress", kind="epic")], done="sw-shape")
        self.assertEqual(a["mode"], "stop")

    def test_accepted_split_epic_does_not_rerun_shape(self):
        rows = [row(E1, "shape", "in-progress", kind="epic", split=True)]
        rows.append(row(F1, "spec", "not-started"))
        a = handoff.decide(rows, done="sw-shape")
        self.assertEqual((a["mode"], a["next_skill"], a["complete"]), ("continue", "sw-spec", [E1]))

    def test_until_stops_after_the_named_station(self):
        a = handoff.decide([row(F1, "spec", "in-progress")], done="sw-spec", until="spec")
        self.assertEqual(a["mode"], "stop")
        self.assertEqual(a["held_by_until"], [F1])

    def test_no_progress_is_a_stop(self):
        a = handoff.decide([row(F1, "spec", "not-started")], done="sw-spec")
        self.assertEqual(a["mode"], "stop")

    def test_empty_board_uses_routed_fallback(self):
        a = handoff.decide([], fallback="sw-shape")
        self.assertEqual((a["mode"], a["next_skill"]), ("continue", "sw-shape"))


class OtherFlows(unittest.TestCase):
    def test_guided_asks_once(self):
        a = handoff.decide([row(F1, "spec", "in-progress")], flow="guided", done="sw-spec")
        self.assertEqual(a["mode"], "confirm")
        self.assertIn("sw-review", a["ask"])

    def test_step_stops_and_names_the_next_station(self):
        a = handoff.decide([row(F1, "spec", "in-progress")], flow="step", done="sw-spec")
        self.assertEqual((a["mode"], a["next_skill"]), ("stop", "sw-review"))

    def test_required_signoff_waits_for_evidence(self):
        a = handoff.decide([row(F1, "review", "in-progress")], signoff="required", done="sw-review")
        self.assertIn("evidence", a["waiting"][0]["why"])


if __name__ == "__main__":
    unittest.main()
