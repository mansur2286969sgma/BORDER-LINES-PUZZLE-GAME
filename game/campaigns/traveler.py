"""Traveler Campaign logic: state management, agency actions, star scoring, and BFS level solver."""

from collections import deque
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from game.core.models import (
    CountrySpec,
    DocumentInstance,
    DocumentSpec,
    TravelerLevelSpec,
    TravelerState,
)
from game.core.rules import RuleEngine, ValidationResult

# Mapping from level action IDs to document IDs
ACTION_TO_DOC_TYPE: Dict[str, str] = {
    "renew_passport": "passport",
    "apply_visa": "visa",
    "request_invitation": "invitation_letter",
    "get_bank_statement": "bank_statement",
    "get_vaccination": "vaccination_certificate",
    "buy_insurance": "travel_insurance",
    "get_transit_permit": "transit_permit",
}


@dataclass(frozen=True)
class TravelerActionSpec:
    """Description and cost/time parameters of a player action in a Traveler level."""

    action_id: str
    label: str
    doc_type: str
    days_cost: int
    money_cost: int
    target_country: str
    description: str


@dataclass
class ActionExecutionOutcome:
    """Result of executing a single agency action in the Traveler campaign."""

    success: bool
    message: str
    days_advanced: int = 0
    money_spent: int = 0
    travel_triggered: bool = False
    validation_result: Optional[ValidationResult] = None


class TravelerSession:
    """Manages active state, actions, hints, and scoring for a single Traveler campaign level."""

    def __init__(
        self,
        level: TravelerLevelSpec,
        engine: RuleEngine,
    ) -> None:
        """Initialize or reset a Traveler level session."""
        self.level: TravelerLevelSpec = level
        self.engine: RuleEngine = engine
        self.state: TravelerState = self._create_initial_state()
        self.unlocked_hints: int = 0
        self.finished: bool = False
        self.won: bool = False
        self.stars_earned: int = 0
        self.last_validation: Optional[ValidationResult] = None
        self.status_log: List[str] = [
            f"Day {self.state.current_day}: Arrived at {self._country_name(self.level.origin)} Travel Bureau."
        ]

    def _country_name(self, cid: str) -> str:
        c = self.engine.countries.get(cid)
        return c.name if c else cid.title()

    def _create_initial_state(self) -> TravelerState:
        return TravelerState(
            name=self.level.traveler_name,
            origin=self.level.origin,
            destination=self.level.destination,
            current_day=self.level.start_day,
            deadline_day=self.level.deadline_day,
            budget=self.level.start_budget,
            declared_bank_balance=self.level.declared_bank_balance,
            transit_countries=list(self.level.transit_countries),
            documents=[d.copy() for d in self.level.initial_documents],
            action_history=[],
        )

    def restart(self) -> None:
        """Instantly reset the level to its initial state."""
        self.state = self._create_initial_state()
        self.finished = False
        self.won = False
        self.stars_earned = 0
        self.last_validation = None
        self.status_log = [
            f"Day {self.state.current_day}: Level restarted. Plan your paperwork carefully!"
        ]

    def reveal_next_hint(self) -> str:
        """Unlock and return the next hint for this level."""
        if not self.level.hints:
            return "No hints available for this level."
        if self.unlocked_hints < len(self.level.hints):
            self.unlocked_hints += 1
        hint_text = self.level.hints[self.unlocked_hints - 1]
        self.status_log.append(f"Hint #{self.unlocked_hints}: {hint_text}")
        return hint_text

    def get_action_specs(self) -> List[TravelerActionSpec]:
        """Build the list of UI/logic action specifications available in this level."""
        specs: List[TravelerActionSpec] = []
        dest_spec: CountrySpec = self.engine.countries[self.level.destination]

        for act_id in self.level.available_actions:
            if act_id == "wait_day":
                specs.append(
                    TravelerActionSpec(
                        action_id="wait_day",
                        label="Wait 1 Day",
                        doc_type="",
                        days_cost=1,
                        money_cost=0,
                        target_country="",
                        description="Advance the calendar by 1 day without spending money.",
                    )
                )
            elif act_id == "travel":
                specs.append(
                    TravelerActionSpec(
                        action_id="travel",
                        label=f"Depart to {dest_spec.name}",
                        doc_type="",
                        days_cost=0,
                        money_cost=0,
                        target_country=self.level.destination,
                        description="Proceed to border control and present your current document dossier.",
                    )
                )
            elif act_id in ACTION_TO_DOC_TYPE:
                doc_type = ACTION_TO_DOC_TYPE[act_id]
                doc_spec: DocumentSpec = self.engine.documents[doc_type]
                if doc_type == "visa":
                    days_cost = dest_spec.visa_processing_days
                    money_cost = dest_spec.visa_fee
                    target = self.level.destination
                    label = f"Apply: {dest_spec.name} Visa"
                elif doc_type == "transit_permit":
                    days_cost = doc_spec.processing_days
                    money_cost = doc_spec.cost
                    target = (
                        self.level.transit_countries[0]
                        if self.level.transit_countries
                        else self.level.destination
                    )
                    t_name = self._country_name(target)
                    label = f"Permit: {t_name} Transit"
                elif doc_type == "invitation_letter":
                    days_cost = doc_spec.processing_days
                    money_cost = doc_spec.cost
                    target = self.level.destination
                    label = doc_spec.action_label
                else:
                    days_cost = doc_spec.processing_days
                    money_cost = doc_spec.cost
                    target = ""
                    label = doc_spec.action_label

                specs.append(
                    TravelerActionSpec(
                        action_id=act_id,
                        label=label,
                        doc_type=doc_type,
                        days_cost=days_cost,
                        money_cost=money_cost,
                        target_country=target,
                        description=doc_spec.description,
                    )
                )
        return specs

    def can_perform_action(
        self,
        action_spec: TravelerActionSpec,
        state: Optional[TravelerState] = None,
    ) -> Tuple[bool, str]:
        """Check whether the player can currently execute action_spec."""
        st = state if state is not None else self.state

        if action_spec.action_id == "travel":
            return True, "Ready to depart for border inspection."

        if action_spec.action_id == "wait_day":
            if st.current_day + 1 > st.deadline_day + 3:
                return False, "Cannot wait any longer: departure deadline has already passed."
            return True, "Advance calendar by 1 day."

        if st.budget < action_spec.money_cost:
            return (
                False,
                f"Insufficient budget: costs ${action_spec.money_cost}, you have ${st.budget}.",
            )

        ok, reason = self.engine.can_apply_for_document(
            st,
            action_spec.doc_type,
            target_country=action_spec.target_country,
        )
        if not ok:
            return False, reason

        return True, f"Takes {action_spec.days_cost}d, costs ${action_spec.money_cost}."

    def execute_action(self, action_id: str) -> ActionExecutionOutcome:
        """Execute an action by ID, mutating self.state and logging the outcome."""
        specs = {s.action_id: s for s in self.get_action_specs()}
        if action_id not in specs:
            return ActionExecutionOutcome(False, f"Action '{action_id}' is not available.")

        spec = specs[action_id]
        can_do, reason = self.can_perform_action(spec)
        if not can_do:
            self.status_log.append(f"Blocked: {reason}")
            return ActionExecutionOutcome(False, reason)

        if action_id == "wait_day":
            self.state.current_day += 1
            self.state.action_history.append("wait_day")
            msg = f"Day {self.state.current_day}: Waited 1 day."
            self.status_log.append(msg)
            return ActionExecutionOutcome(True, msg, days_advanced=1, money_spent=0)

        if action_id == "travel":
            self.state.action_history.append("travel")
            result = self.engine.validate(
                self.state,
                destination=self.level.destination,
                date=self.state.current_day,
            )
            self.last_validation = result
            self.finished = True
            self.won = result.passed
            if self.won:
                self.stars_earned = self.calculate_stars()
                msg = f"BORDER CLEARED! Welcome to {self._country_name(self.level.destination)}!"
            else:
                self.stars_earned = 0
                msg = f"ENTRY DENIED at {self._country_name(self.level.destination)} Border Control."
            self.status_log.append(msg)
            return ActionExecutionOutcome(
                success=result.passed,
                message=msg,
                travel_triggered=True,
                validation_result=result,
            )

        # Document application/renewal action
        self._apply_document_action_to_state(self.state, spec)
        doc_spec = self.engine.documents[spec.doc_type]
        new_doc = self.state.documents[-1]
        msg = (
            f"Day {self.state.current_day}: Obtained {doc_spec.name} "
            f"(Valid until Day {new_doc.expiry_day}, -${spec.money_cost}, +{spec.days_cost}d)."
        )
        self.status_log.append(msg)
        return ActionExecutionOutcome(
            True,
            msg,
            days_advanced=spec.days_cost,
            money_spent=spec.money_cost,
        )

    def _apply_document_action_to_state(
        self,
        st: TravelerState,
        spec: TravelerActionSpec,
    ) -> None:
        """Mutate st in-place by paying money, advancing days, and issuing the document."""
        doc_spec = self.engine.documents[spec.doc_type]
        st.budget -= spec.money_cost
        st.current_day += spec.days_cost
        st.action_history.append(spec.action_id)

        issue_day = st.current_day
        expiry_day = issue_day + doc_spec.validity_days
        extra = {}
        if spec.doc_type == "bank_statement":
            extra["balance"] = st.declared_bank_balance

        # Replace existing document of the same (doc_type, target_country) so the dossier stays clean
        st.documents = [
            d
            for d in st.documents
            if not (d.doc_type == spec.doc_type and d.target_country == spec.target_country)
        ]
        st.documents.append(
            DocumentInstance(
                doc_type=spec.doc_type,
                owner_name=st.name,
                nationality=st.origin,
                target_country=spec.target_country,
                issue_day=issue_day,
                expiry_day=expiry_day,
                stamped=True,
                extra_data=extra,
            )
        )

    def calculate_stars(self) -> int:
        """Compute a 1 to 3 star rating based on days used and remaining budget."""
        if not self.won:
            return 0
        days_used = self.state.current_day - self.level.start_day
        budget_left = self.state.budget

        t3 = self.level.star_thresholds.get("three_stars", {})
        if (
            days_used <= t3.get("max_days_used", 999)
            and budget_left >= t3.get("min_budget_left", 0)
        ):
            return 3

        t2 = self.level.star_thresholds.get("two_stars", {})
        if (
            days_used <= t2.get("max_days_used", 999)
            and budget_left >= t2.get("min_budget_left", 0)
        ):
            return 2

        return 1


def find_winning_action_sequence(
    level: TravelerLevelSpec,
    engine: RuleEngine,
) -> Optional[List[str]]:
    """Run a BFS over available agency actions to verify the level is solvable.

    Returns a winning list of action IDs ending with 'travel', or None if unsolvable.
    """
    session = TravelerSession(level, engine)
    action_specs = [s for s in session.get_action_specs() if s.action_id != "wait_day"]
    travel_spec = next((s for s in action_specs if s.action_id == "travel"), None)
    doc_specs = [s for s in action_specs if s.action_id != "travel"]

    if travel_spec is None:
        return None

    queue = deque([session.state.copy()])
    visited = set()

    while queue:
        curr = queue.popleft()

        # Check if departing right now wins the level
        val = engine.validate(curr, destination=level.destination, date=curr.current_day)
        if val.passed:
            return curr.action_history + ["travel"]

        if curr.current_day >= curr.deadline_day:
            continue

        for spec in doc_specs:
            # Avoid repeating the exact same action twice in a single path
            if spec.action_id in curr.action_history:
                continue
            can_do, _ = session.can_perform_action(spec, state=curr)
            if not can_do:
                continue
            nxt = curr.copy()
            session._apply_document_action_to_state(nxt, spec)
            if nxt.current_day > nxt.deadline_day or nxt.budget < 0:
                continue
            sig = (
                nxt.current_day,
                nxt.budget,
                tuple((d.doc_type, d.target_country, d.expiry_day) for d in nxt.documents),
            )
            if sig not in visited:
                visited.add(sig)
                queue.append(nxt)

    return None
