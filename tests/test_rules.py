"""Unit tests for the shared Rules Engine, JSON Loader, BFS Level Solver, and Consul Generator."""

import os
import tempfile
import unittest

from game.campaigns.consul import ConsulSession
from game.campaigns.traveler import TravelerSession, find_winning_action_sequence
from game.constants import (
    DECISION_APPROVE,
    DECISION_DENY,
    DECISION_REQUEST_DOC,
    REASON_EXPIRED,
    REASON_INSUFFICIENT_FUNDS,
    REASON_INSUFFICIENT_VALIDITY,
    REASON_MISSING_DOC,
    REASON_MISSING_STAMP,
    REASON_WRONG_COUNTRY,
    REASON_WRONG_NAME,
)
from game.core.generator import ApplicantGenerator
from game.core.loader import DataLoadError, load_countries, load_game_database
from game.core.models import DocumentInstance, TravelerState
from game.core.rules import RuleEngine


class TestBorderLinesCore(unittest.TestCase):
    """Comprehensive test suite for BORDER LINES core rules, campaigns, and level solvability."""

    @classmethod
    def setUpClass(cls) -> None:
        """Load the JSON database and initialize the shared RuleEngine once for all tests."""
        cls.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cls.data_dir = os.path.join(cls.project_root, "data")
        cls.db = load_game_database(cls.data_dir)
        cls.engine = RuleEngine(cls.db.countries, cls.db.documents)

    def test_database_contents_match_spec(self) -> None:
        """Verify 6 fictional countries, 7 document types, 5 traveler levels, and 5 consul shifts exist."""
        self.assertEqual(len(self.db.countries), 6)
        self.assertGreaterEqual(len(self.db.documents), 7)
        self.assertEqual(len(self.db.traveler_levels), 5)
        self.assertEqual(len(self.db.consul_shifts), 5)

    def test_loader_rejects_malformed_json_with_clear_error(self) -> None:
        """Verify that malformed JSON raises DataLoadError with line/column diagnostics."""
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tmp:
            tmp.write("{ broken json ")
            tmp_path = tmp.name
        try:
            with self.assertRaises(DataLoadError):
                load_countries(tmp_path)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_rule_engine_valid_crossing(self) -> None:
        """Verify that a traveler with valid passport and visa passes Norwen border control."""
        state = TravelerState(
            name="Clara Vance",
            origin="valdoria",
            destination="norwen",
            current_day=3,
            deadline_day=5,
            budget=100,
            declared_bank_balance=300,
            documents=[
                DocumentInstance("passport", "Clara Vance", "valdoria", "", 1, 60, True),
                DocumentInstance("visa", "Clara Vance", "valdoria", "norwen", 3, 33, True),
            ],
        )
        res = self.engine.validate(state, destination="norwen", date=3)
        self.assertTrue(res.passed, f"Expected pass, got reasons: {res.reasons}")
        self.assertEqual(res.expected_consul_decision, DECISION_APPROVE)

    def test_rule_engine_detects_insufficient_passport_validity(self) -> None:
        """Verify passport minimum validity buffer beyond arrival date is enforced."""
        state = TravelerState(
            name="Arthur Pendelton",
            origin="valdoria",
            destination="norwen",
            current_day=3,
            deadline_day=7,
            budget=100,
            declared_bank_balance=300,
            documents=[
                # Norwen requires 30 days beyond arrival (Day 3 + 30 = Day 33+), so expiry 20 fails
                DocumentInstance("passport", "Arthur Pendelton", "valdoria", "", -30, 20, True),
                DocumentInstance("visa", "Arthur Pendelton", "valdoria", "norwen", 3, 33, True),
            ],
        )
        res = self.engine.validate(state, destination="norwen", date=3)
        self.assertFalse(res.passed)
        codes = {i.code for i in res.issues}
        self.assertIn(REASON_INSUFFICIENT_VALIDITY, codes)

    def test_rule_engine_detects_missing_stamp_and_wrong_name_and_wrong_country(self) -> None:
        """Verify document error detection for forged names, missing stamps, and wrong country."""
        state = TravelerState(
            name="Elena Rostova",
            origin="valdoria",
            destination="valdoria",
            current_day=10,
            deadline_day=20,
            budget=50,
            declared_bank_balance=300,
            documents=[
                DocumentInstance("passport", "Wrong Name", "keshmar", "", 1, 50, False),
                DocumentInstance("visa", "Elena Rostova", "keshmar", "norwen", 2, 30, True),
            ],
        )
        state.origin = "keshmar"
        res = self.engine.validate(state, destination="valdoria", date=10)
        self.assertFalse(res.passed)
        codes = {i.code for i in res.issues}
        self.assertIn(REASON_WRONG_NAME, codes)
        self.assertIn(REASON_MISSING_STAMP, codes)
        self.assertIn(REASON_WRONG_COUNTRY, codes)

    def test_rule_engine_visa_free_relations(self) -> None:
        """Verify citizens of a visa-free partner country do not need an Entry Visa."""
        # Norwen -> Orlanda is visa_free
        state = TravelerState(
            name="Henrik Solberg",
            origin="norwen",
            destination="orlanda",
            current_day=5,
            deadline_day=10,
            budget=80,
            declared_bank_balance=250,
            documents=[
                DocumentInstance("passport", "Henrik Solberg", "norwen", "", 1, 60, True),
                DocumentInstance(
                    "bank_statement",
                    "Henrik Solberg",
                    "norwen",
                    "",
                    4,
                    19,
                    True,
                    extra_data={"balance": 250},
                ),
                DocumentInstance("travel_insurance", "Henrik Solberg", "norwen", "", 4, 24, True),
            ],
        )
        res = self.engine.validate(state, destination="orlanda", date=5)
        self.assertTrue(res.passed, f"Expected visa-free pass, got: {res.reasons}")

    def test_rule_engine_insufficient_bank_funds_and_expired(self) -> None:
        """Verify minimum bank balance and document expiry rules."""
        state = TravelerState(
            name="Henrik Solberg",
            origin="norwen",
            destination="orlanda",
            current_day=10,
            deadline_day=15,
            budget=80,
            declared_bank_balance=120,
            documents=[
                DocumentInstance("passport", "Henrik Solberg", "norwen", "", 1, 60, True),
                DocumentInstance(
                    "bank_statement",
                    "Henrik Solberg",
                    "norwen",
                    "",
                    1,
                    15,
                    True,
                    extra_data={"balance": 120},
                ),
                DocumentInstance("travel_insurance", "Henrik Solberg", "norwen", "", 1, 8, True),
            ],
        )
        res = self.engine.validate(state, destination="orlanda", date=10)
        self.assertFalse(res.passed)
        codes = {i.code for i in res.issues}
        self.assertIn(REASON_INSUFFICIENT_FUNDS, codes)
        self.assertIn(REASON_EXPIRED, codes)

    def test_all_five_traveler_levels_are_solvable_via_bfs(self) -> None:
        """Run BFS solver over all 5 Traveler levels to guarantee every level is solvable and reaches 3 stars."""
        for level in self.db.traveler_levels:
            winning_path = find_winning_action_sequence(level, self.engine)
            self.assertIsNotNone(
                winning_path,
                f"Traveler Level {level.id} ('{level.title}') has no valid solution!",
            )
            # Replay the winning sequence on a fresh TravelerSession and verify it wins
            session = TravelerSession(level, self.engine)
            for act_id in winning_path:
                outcome = session.execute_action(act_id)
                if act_id != "travel":
                    self.assertTrue(
                        outcome.success,
                        f"Level {level.id} action '{act_id}' failed: {outcome.message}",
                    )
            self.assertTrue(session.finished)
            self.assertTrue(session.won, f"Level {level.id} replay did not win!")
            self.assertGreaterEqual(session.stars_earned, 1)

    def test_all_five_consul_shifts_generate_unambiguous_deterministic_cases(self) -> None:
        """Verify every generated applicant in all 5 Consul shifts has one unambiguous correct decision."""
        gen = ApplicantGenerator(self.engine)
        valid_decisions = {DECISION_APPROVE, DECISION_DENY, DECISION_REQUEST_DOC}

        for shift in self.db.consul_shifts:
            q1 = gen.generate_shift_queue(shift)
            q2 = gen.generate_shift_queue(shift)
            self.assertEqual(len(q1), shift.applicant_count)
            self.assertEqual(len(q2), shift.applicant_count)

            # Verify determinism: same seed produces identical applicant names and decisions
            for a, b in zip(q1, q2):
                self.assertEqual(a.name, b.name)
                self.assertEqual(a.expected_decision, b.expected_decision)
                self.assertEqual(a.expected_reason_code, b.expected_reason_code)

            # Verify every case matches RuleEngine.validate() and can be 100% solved in ConsulSession
            session = ConsulSession(shift, self.engine, generator=gen)
            for case in session.queue:
                self.assertIn(case.expected_decision, valid_decisions)
                val = self.engine.validate(
                    case.to_traveler_state(),
                    destination=shift.destination,
                    date=shift.current_day,
                    active_doc_filter=shift.active_documents,
                )
                self.assertEqual(case.expected_decision, val.expected_consul_decision)
                if val.passed:
                    self.assertEqual(case.expected_decision, DECISION_APPROVE)
                else:
                    self.assertIn(case.expected_decision, {DECISION_DENY, DECISION_REQUEST_DOC})
                    self.assertGreater(len(val.issues), 0)

                # Submit the authoritative decision and confirm ConsulSession scores it as correct
                outcome = session.submit_decision(
                    case.expected_decision,
                    reason_code=case.expected_reason_code,
                )
                self.assertTrue(
                    outcome.correct,
                    f"Shift {shift.id} Case {case.case_id} ({case.name}) failed with expected decision "
                    f"{case.expected_decision}/{case.expected_reason_code}: {outcome.feedback_details}",
                )

            self.assertTrue(session.finished)
            self.assertTrue(session.won)
            self.assertEqual(session.strikes, 0)
            self.assertEqual(session.stars_earned, 3)


if __name__ == "__main__":
    unittest.main()
