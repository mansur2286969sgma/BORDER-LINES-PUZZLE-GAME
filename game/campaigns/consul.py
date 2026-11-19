"""Consul Campaign logic: applicant queue, document discrepancy flagging, decisions, and scoring."""

from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from game.constants import (
    DECISION_APPROVE,
    DECISION_DENY,
    DECISION_REQUEST_DOC,
    DENIAL_REASON_LABELS,
    REASON_EXPIRED,
    REASON_INSUFFICIENT_VALIDITY,
    REASON_MISSING_DOC,
    REASON_VALID,
)
from game.core.generator import ApplicantGenerator
from game.core.models import ApplicantCase, ConsulShiftSpec
from game.core.rules import RuleEngine, ValidationResult


@dataclass
class ConsulDecisionOutcome:
    """Outcome of a single consular decision on an applicant."""

    correct: bool
    player_decision: str
    player_reason_code: str
    expected_decision: str
    expected_reason_code: str
    money_delta: int
    strike_added: bool
    feedback_title: str
    feedback_details: List[str] = field(default_factory=list)


class ConsulSession:
    """Manages active state, applicant queue, flagged discrepancies, and scoring for a Consul shift."""

    def __init__(
        self,
        shift: ConsulShiftSpec,
        engine: RuleEngine,
        generator: Optional[ApplicantGenerator] = None,
    ) -> None:
        """Initialize a Consul shift session."""
        self.shift: ConsulShiftSpec = shift
        self.engine: RuleEngine = engine
        self.generator: ApplicantGenerator = generator or ApplicantGenerator(engine)
        self.queue: List[ApplicantCase] = []
        self.current_index: int = 0
        self.correct_count: int = 0
        self.incorrect_count: int = 0
        self.strikes: int = 0
        self.earnings: int = 0
        self.flagged_fields: Set[Tuple[str, str]] = set()
        self.missed_rules_counter: Counter = Counter()
        self.time_remaining: float = float(shift.time_limit_seconds)
        self.finished: bool = False
        self.won: bool = False
        self.stars_earned: int = 0
        self.last_outcome: Optional[ConsulDecisionOutcome] = None
        self.restart()

    def restart(self) -> None:
        """Reset the shift and regenerate the deterministic applicant queue."""
        self.queue = self.generator.generate_shift_queue(self.shift)
        self.current_index = 0
        self.correct_count = 0
        self.incorrect_count = 0
        self.strikes = 0
        self.earnings = 0
        self.flagged_fields.clear()
        self.missed_rules_counter.clear()
        self.time_remaining = float(self.shift.time_limit_seconds)
        self.finished = False
        self.won = False
        self.stars_earned = 0
        self.last_outcome = None

    @property
    def current_applicant(self) -> Optional[ApplicantCase]:
        """Return the applicant currently at the desk, or None if the queue is finished."""
        if 0 <= self.current_index < len(self.queue) and not self.finished:
            return self.queue[self.current_index]
        return None

    def toggle_flag_field(self, doc_type: str, field_name: str) -> bool:
        """Toggle a discrepancy highlight on a document field. Returns True if now flagged."""
        key = (doc_type, field_name)
        if key in self.flagged_fields:
            self.flagged_fields.remove(key)
            return False
        self.flagged_fields.add(key)
        return True

    def update_timer(self, dt: float) -> bool:
        """Advance the shift countdown timer if active. Returns True if time just expired."""
        if self.finished or self.shift.time_limit_seconds <= 0:
            return False
        self.time_remaining = max(0.0, self.time_remaining - dt)
        if self.time_remaining <= 0.0:
            self.finished = True
            self.won = self.strikes < self.shift.max_strikes and self.correct_count > 0
            self.stars_earned = self.calculate_stars()
            return True
        return False

    def submit_decision(
        self,
        decision: str,
        reason_code: str = "",
    ) -> ConsulDecisionOutcome:
        """Evaluate the player's decision (APPROVE, DENY, or REQUEST_MISSING_DOCUMENT) against RuleEngine."""
        applicant = self.current_applicant
        if applicant is None:
            return ConsulDecisionOutcome(
                correct=False,
                player_decision=decision,
                player_reason_code=reason_code,
                expected_decision="",
                expected_reason_code="",
                money_delta=0,
                strike_added=False,
                feedback_title="Shift already finished.",
            )

        val_result: ValidationResult = self.engine.validate(
            applicant.to_traveler_state(),
            destination=self.shift.destination,
            date=self.shift.current_day,
            active_doc_filter=self.shift.active_documents,
        )

        expected_decision = val_result.expected_consul_decision
        expected_code = val_result.primary_code
        valid_codes = {issue.code for issue in val_result.issues}

        is_correct = False
        if decision == DECISION_APPROVE:
            is_correct = val_result.passed
        elif decision == DECISION_REQUEST_DOC:
            is_correct = (not val_result.passed) and (REASON_MISSING_DOC in valid_codes)
        elif decision == DECISION_DENY:
            if not val_result.passed:
                # If no specific reason was required or reason matches any actual issue
                if not reason_code or reason_code in valid_codes:
                    is_correct = True
                # Also accept expired/insufficient_validity interchangeably if the player flagged the expiry date
                elif reason_code in (REASON_EXPIRED, REASON_INSUFFICIENT_VALIDITY) and (
                    valid_codes & {REASON_EXPIRED, REASON_INSUFFICIENT_VALIDITY}
                ):
                    is_correct = True
                # Also accept DENY with REASON_MISSING_DOC if a document is missing
                elif reason_code == REASON_MISSING_DOC and REASON_MISSING_DOC in valid_codes:
                    is_correct = True

        # Bonus check: if the player flagged the exact discrepancy field on the desk and chose DENY, give credit!
        if not is_correct and decision == DECISION_DENY and not val_result.passed:
            for issue in val_result.issues:
                if (issue.doc_type, issue.field_name) in self.flagged_fields:
                    is_correct = True
                    break

        if is_correct:
            self.correct_count += 1
            money_delta = self.shift.pay_per_correct
            # Small bonus for flagging at least one real issue before denying
            if not val_result.passed and self.flagged_fields:
                for issue in val_result.issues:
                    if (issue.doc_type, issue.field_name) in self.flagged_fields:
                        money_delta += 5
                        break
            self.earnings += money_delta
            outcome = ConsulDecisionOutcome(
                correct=True,
                player_decision=decision,
                player_reason_code=reason_code,
                expected_decision=expected_decision,
                expected_reason_code=expected_code,
                money_delta=money_delta,
                strike_added=False,
                feedback_title=f"CORRECT! (+${money_delta})",
                feedback_details=(
                    ["Applicant dossier satisfied all entry rules."]
                    if val_result.passed
                    else list(val_result.reasons)
                ),
            )
        else:
            self.incorrect_count += 1
            self.strikes += 1
            money_delta = -self.shift.penalty_per_wrong
            self.earnings = max(0, self.earnings + money_delta)
            missed_key = expected_code if expected_code != REASON_VALID else "false_rejection"
            self.missed_rules_counter[missed_key] += 1

            if val_result.passed:
                details = ["This applicant's documents were completely valid—should have been APPROVED."]
            else:
                details = list(val_result.reasons)

            outcome = ConsulDecisionOutcome(
                correct=False,
                player_decision=decision,
                player_reason_code=reason_code,
                expected_decision=expected_decision,
                expected_reason_code=expected_code,
                money_delta=money_delta,
                strike_added=True,
                feedback_title=f"CITATION ISSUED! Strike {self.strikes}/{self.shift.max_strikes} (-${self.shift.penalty_per_wrong})",
                feedback_details=details,
            )

        self.last_outcome = outcome
        self.flagged_fields.clear()
        self.current_index += 1

        if self.strikes >= self.shift.max_strikes:
            self.finished = True
            self.won = False
            self.stars_earned = 0
        elif self.current_index >= len(self.queue):
            self.finished = True
            self.won = True
            self.stars_earned = self.calculate_stars()

        return outcome

    def calculate_stars(self) -> int:
        """Compute a 1 to 3 star rating for a completed shift based on strikes."""
        if not self.won:
            return 0
        if self.strikes == 0:
            return 3
        if self.strikes == 1:
            return 2
        return 1

    def most_missed_rule_description(self) -> str:
        """Return a human-readable summary of the rule the player missed most often."""
        if not self.missed_rules_counter:
            return "None — spotless inspection record!"
        top_code, count = self.missed_rules_counter.most_common(1)[0]
        if top_code == "false_rejection":
            return f"False Rejection of Valid Dossier ({count}x)"
        label = DENIAL_REASON_LABELS.get(top_code, top_code.replace("_", " ").title())
        return f"{label} ({count}x)"
