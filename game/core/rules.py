"""Shared data-driven rules engine for BORDER LINES (pure Python, no Pygame imports)."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from game.constants import (
    DECISION_APPROVE,
    DECISION_DENY,
    DECISION_REQUEST_DOC,
    REASON_DEADLINE_PASSED,
    REASON_EXPIRED,
    REASON_INSUFFICIENT_FUNDS,
    REASON_INSUFFICIENT_VALIDITY,
    REASON_MISSING_DOC,
    REASON_MISSING_PREREQUISITE,
    REASON_MISSING_STAMP,
    REASON_OVER_BUDGET,
    REASON_VALID,
    REASON_WRONG_COUNTRY,
    REASON_WRONG_NAME,
)
from game.core.models import CountrySpec, DocumentInstance, DocumentSpec, TravelerState


@dataclass(frozen=True)
class ValidationIssue:
    """A single rule violation discovered during validation."""

    code: str
    doc_type: str
    field_name: str
    message: str


@dataclass
class ValidationResult:
    """Output of RuleEngine.validate() shared by both Traveler and Consul campaigns."""

    passed: bool
    reasons: List[str] = field(default_factory=list)
    issues: List[ValidationIssue] = field(default_factory=list)

    @property
    def primary_code(self) -> str:
        """Return the primary canonical failure reason code, or REASON_VALID if passed."""
        if self.passed or not self.issues:
            return REASON_VALID
        return self.issues[0].code

    @property
    def expected_consul_decision(self) -> str:
        """Return the canonical decision expected from a consular officer for this result."""
        if self.passed:
            return DECISION_APPROVE
        codes = {issue.code for issue in self.issues}
        if codes == {REASON_MISSING_DOC}:
            return DECISION_REQUEST_DOC
        return DECISION_DENY


class RuleEngine:
    """Data-driven border and visa validation engine powering both campaigns."""

    def __init__(
        self,
        countries: Dict[str, CountrySpec],
        documents: Dict[str, DocumentSpec],
    ) -> None:
        """Initialize the engine with loaded country and document catalogs."""
        self.countries: Dict[str, CountrySpec] = countries
        self.documents: Dict[str, DocumentSpec] = documents

    def get_required_documents(
        self,
        origin: str,
        destination: str,
        transit_countries: Optional[List[str]] = None,
        active_doc_filter: Optional[Tuple[str, ...]] = None,
    ) -> List[Tuple[str, str]]:
        """Return a list of (doc_type, target_country_id) required for the journey.

        target_country_id is empty string '' for non-country-specific documents.
        """
        if destination not in self.countries:
            raise ValueError(f"Unknown destination country: {destination}")

        dest_spec = self.countries[destination]
        required: List[Tuple[str, str]] = []

        for doc_id in dest_spec.required_documents:
            if active_doc_filter is not None and doc_id not in active_doc_filter:
                continue
            if doc_id == "visa" and dest_spec.is_visa_free_for(origin):
                continue
            doc_spec = self.documents.get(doc_id)
            target = destination if (doc_spec and doc_spec.target_country_specific) else ""
            required.append((doc_id, target))

        # Check transit countries requiring a transit permit
        if transit_countries:
            for transit_id in transit_countries:
                if active_doc_filter is not None and "transit_permit" not in active_doc_filter:
                    continue
                transit_spec = self.countries.get(transit_id)
                needs_permit = False
                if transit_spec:
                    if "transit_permit" in transit_spec.required_documents:
                        needs_permit = True
                    elif dest_spec.relations.get(transit_id) == "transit_permit_required":
                        needs_permit = True
                if needs_permit and ("transit_permit", transit_id) not in required:
                    required.append(("transit_permit", transit_id))

        return required

    def can_apply_for_document(
        self,
        state: TravelerState,
        doc_type: str,
        target_country: str = "",
    ) -> Tuple[bool, str]:
        """Check if a traveler currently satisfies the prerequisites to apply for doc_type."""
        if doc_type not in self.documents:
            return False, f"Unknown document type '{doc_type}'."

        doc_spec = self.documents[doc_type]
        prereqs = list(doc_spec.prerequisites)

        # Destination country may specify extra visa prerequisites (e.g., invitation_letter)
        effective_target = target_country or state.destination
        if doc_type == "visa" and effective_target in self.countries:
            country_prereqs = self.countries[effective_target].visa_prerequisites
            for cp in country_prereqs:
                if cp not in prereqs:
                    prereqs.append(cp)

        for prereq_id in prereqs:
            prereq_spec = self.documents.get(prereq_id)
            prereq_name = prereq_spec.name if prereq_spec else prereq_id
            # Find any matching prerequisite document in state
            candidates = [d for d in state.documents if d.doc_type == prereq_id]
            if not candidates:
                return (
                    False,
                    f"Cannot apply for {doc_spec.name}: requires a valid {prereq_name} first.",
                )
            latest = candidates[-1]
            if latest.expiry_day < state.current_day:
                return (
                    False,
                    f"Cannot apply for {doc_spec.name}: your {prereq_name} is expired (Day {latest.expiry_day}).",
                )
            if prereq_spec and prereq_spec.target_country_specific and effective_target:
                if latest.target_country != effective_target:
                    target_name = self.countries[effective_target].name if effective_target in self.countries else effective_target
                    return (
                        False,
                        f"Cannot apply for {doc_spec.name}: your {prereq_name} is not issued for {target_name}.",
                    )

        return True, "Prerequisites satisfied."

    def validate(
        self,
        applicant_or_traveler_state: TravelerState,
        destination: str,
        date: int,
        active_doc_filter: Optional[Tuple[str, ...]] = None,
    ) -> ValidationResult:
        """Validate a traveler or applicant against all border rules for destination on date.

        Returns a ValidationResult with pass/fail, human-readable reasons, and structured issues.
        """
        state = applicant_or_traveler_state
        issues: List[ValidationIssue] = []

        if destination not in self.countries:
            issues.append(
                ValidationIssue(
                    code=REASON_WRONG_COUNTRY,
                    doc_type="destination",
                    field_name="destination",
                    message=f"Destination country '{destination}' does not exist in border registry.",
                )
            )
            return ValidationResult(passed=False, reasons=[i.message for i in issues], issues=issues)

        dest_spec = self.countries[destination]

        # 1. Check travel deadline and budget constraints (relevant for Traveler campaign)
        if date > state.deadline_day:
            issues.append(
                ValidationIssue(
                    code=REASON_DEADLINE_PASSED,
                    doc_type="schedule",
                    field_name="current_day",
                    message=(
                        f"Departure deadline missed: arrived on Day {date}, "
                        f"but deadline was Day {state.deadline_day}."
                    ),
                )
            )

        if state.budget < 0:
            issues.append(
                ValidationIssue(
                    code=REASON_OVER_BUDGET,
                    doc_type="budget",
                    field_name="budget",
                    message=f"Budget exceeded: balance is ${state.budget}.",
                )
            )

        # 2. Determine required documents for this origin -> destination (+ transit)
        required_docs = self.get_required_documents(
            origin=state.origin,
            destination=destination,
            transit_countries=state.transit_countries,
            active_doc_filter=active_doc_filter,
        )

        # 3. Validate each required document
        for req_doc_type, expected_target in required_docs:
            doc_spec = self.documents[req_doc_type]
            # Look up documents of this type
            matching_type_docs = [d for d in state.documents if d.doc_type == req_doc_type]
            if not matching_type_docs:
                target_suffix = ""
                if expected_target and expected_target in self.countries:
                    target_suffix = f" for {self.countries[expected_target].name}"
                issues.append(
                    ValidationIssue(
                        code=REASON_MISSING_DOC,
                        doc_type=req_doc_type,
                        field_name="document",
                        message=f"Missing required document: {doc_spec.name}{target_suffix}.",
                    )
                )
                continue

            # If multiple of same type exist (e.g., transit permit or renewed passport), pick best matching or latest
            doc: Optional[DocumentInstance] = None
            if expected_target:
                exact_target = [d for d in matching_type_docs if d.target_country == expected_target]
                doc = exact_target[-1] if exact_target else matching_type_docs[-1]
            else:
                doc = matching_type_docs[-1]

            self._validate_single_document(
                doc=doc,
                doc_spec=doc_spec,
                state=state,
                dest_spec=dest_spec,
                expected_target=expected_target,
                date=date,
                issues=issues,
            )

        # 4. Also check any extra presented documents that are in active_doc_filter for obvious errors
        checked_ids = {id(d) for d in state.documents if any(d.doc_type == r[0] for r in required_docs)}
        for doc in state.documents:
            if id(doc) in checked_ids:
                continue
            if active_doc_filter is not None and doc.doc_type not in active_doc_filter:
                continue
            doc_spec = self.documents.get(doc.doc_type)
            if not doc_spec:
                continue
            expected_target = destination if doc_spec.target_country_specific else ""
            if doc.doc_type == "transit_permit" and state.transit_countries:
                expected_target = state.transit_countries[0]
            self._validate_single_document(
                doc=doc,
                doc_spec=doc_spec,
                state=state,
                dest_spec=dest_spec,
                expected_target=expected_target,
                date=date,
                issues=issues,
            )

        # 5. Check Visa prerequisite rules (e.g. Visa requires valid Invitation Letter if destination demands it)
        has_visa = any(d.doc_type == "visa" for d in state.documents)
        if has_visa and not dest_spec.is_visa_free_for(state.origin):
            for prereq_id in dest_spec.visa_prerequisites:
                if prereq_id == "passport":
                    continue
                if active_doc_filter is not None and prereq_id not in active_doc_filter:
                    continue
                prereq_docs = [d for d in state.documents if d.doc_type == prereq_id]
                prereq_name = self.documents[prereq_id].name if prereq_id in self.documents else prereq_id
                if not prereq_docs:
                    # Avoid duplicate message if already flagged as missing required document
                    already_missing = any(
                        i.code == REASON_MISSING_DOC and i.doc_type == prereq_id for i in issues
                    )
                    if not already_missing:
                        issues.append(
                            ValidationIssue(
                                code=REASON_MISSING_PREREQUISITE,
                                doc_type="visa",
                                field_name="prerequisite",
                                message=(
                                    f"{dest_spec.name} Entry Visa is invalid without its prerequisite "
                                    f"{prereq_name}."
                                ),
                            )
                        )

        # 6. Check minimum bank balance rule when bank_statement is required or presented
        bank_docs = [d for d in state.documents if d.doc_type == "bank_statement"]
        if bank_docs and dest_spec.min_bank_balance > 0:
            bdoc = bank_docs[-1]
            balance = int(bdoc.extra_data.get("balance", state.declared_bank_balance))
            if balance < dest_spec.min_bank_balance:
                issues.append(
                    ValidationIssue(
                        code=REASON_INSUFFICIENT_FUNDS,
                        doc_type="bank_statement",
                        field_name="balance",
                        message=(
                            f"Bank Statement balance (${balance}) is below {dest_spec.name}'s "
                            f"minimum requirement of ${dest_spec.min_bank_balance}."
                        ),
                    )
                )

        reasons = [issue.message for issue in issues]
        return ValidationResult(passed=len(issues) == 0, reasons=reasons, issues=issues)

    def _validate_single_document(
        self,
        doc: DocumentInstance,
        doc_spec: DocumentSpec,
        state: TravelerState,
        dest_spec: CountrySpec,
        expected_target: str,
        date: int,
        issues: List[ValidationIssue],
    ) -> None:
        """Inspect a single document instance for name, stamp, country, and expiry errors."""
        # Owner name check
        if doc.owner_name.strip().lower() != state.name.strip().lower():
            issues.append(
                ValidationIssue(
                    code=REASON_WRONG_NAME,
                    doc_type=doc.doc_type,
                    field_name="owner_name",
                    message=(
                        f"{doc_spec.name} name mismatch: issued to '{doc.owner_name}', "
                        f"but traveler is '{state.name}'."
                    ),
                )
            )

        # Official stamp check
        if doc_spec.requires_stamp and not doc.stamped:
            issues.append(
                ValidationIssue(
                    code=REASON_MISSING_STAMP,
                    doc_type=doc.doc_type,
                    field_name="stamped",
                    message=f"{doc_spec.name} is missing its official bureau authentication stamp.",
                )
            )

        # Target country check
        if doc_spec.target_country_specific and expected_target:
            if doc.target_country != expected_target:
                actual_name = (
                    self.countries[doc.target_country].name
                    if doc.target_country in self.countries
                    else (doc.target_country or "Unspecified")
                )
                expected_name = (
                    self.countries[expected_target].name
                    if expected_target in self.countries
                    else expected_target
                )
                issues.append(
                    ValidationIssue(
                        code=REASON_WRONG_COUNTRY,
                        doc_type=doc.doc_type,
                        field_name="target_country",
                        message=(
                            f"{doc_spec.name} is valid for {actual_name}, "
                            f"not for {expected_name}."
                        ),
                    )
                )

        # Expiry & minimum passport validity check
        if doc.expiry_day < date:
            issues.append(
                ValidationIssue(
                    code=REASON_EXPIRED,
                    doc_type=doc.doc_type,
                    field_name="expiry_day",
                    message=(
                        f"{doc_spec.name} expired on Day {doc.expiry_day} "
                        f"(current travel date is Day {date})."
                    ),
                )
            )
        elif doc.doc_type == "passport":
            min_valid_until = date + dest_spec.passport_min_validity_days
            if doc.expiry_day < min_valid_until:
                issues.append(
                    ValidationIssue(
                        code=REASON_INSUFFICIENT_VALIDITY,
                        doc_type="passport",
                        field_name="expiry_day",
                        message=(
                            f"Passport expires on Day {doc.expiry_day}, but {dest_spec.name} requires "
                            f"at least {dest_spec.passport_min_validity_days} days validity beyond "
                            f"Day {date} (must be valid until Day {min_valid_until}+)."
                        ),
                    )
                )
