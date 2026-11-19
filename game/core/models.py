"""Pure Python data models for countries, documents, applicants, and campaign levels."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class FlagSpec:
    """Procedural flag specification for a fictional country."""

    style: str
    colors: Tuple[Tuple[int, int, int], ...]
    emblem: str = "none"
    emblem_color: Tuple[int, int, int] = (255, 255, 255)


@dataclass(frozen=True)
class CountrySpec:
    """Definition of a fictional country and its border entry rules."""

    id: str
    name: str
    motto: str
    description: str
    map_pos: Tuple[int, int]
    flag: FlagSpec
    visa_processing_days: int
    visa_fee: int
    passport_min_validity_days: int
    min_bank_balance: int
    required_documents: Tuple[str, ...]
    visa_prerequisites: Tuple[str, ...]
    relations: Dict[str, str]

    def is_visa_free_for(self, origin_country_id: str) -> bool:
        """Return True if citizens of origin_country_id can enter without a visa."""
        if origin_country_id == self.id:
            return True
        return self.relations.get(origin_country_id, "visa_required") == "visa_free"


@dataclass(frozen=True)
class DocumentSpec:
    """Definition of a document type and its issuance rules."""

    id: str
    name: str
    short_name: str
    issuer: str
    action_label: str
    description: str
    validity_days: int
    processing_days: int
    cost: int
    prerequisites: Tuple[str, ...]
    requires_stamp: bool
    target_country_specific: bool
    common_errors: Tuple[str, ...]


@dataclass
class DocumentInstance:
    """A concrete document held by a traveler or presented by an applicant."""

    doc_type: str
    owner_name: str
    nationality: str
    target_country: str
    issue_day: int
    expiry_day: int
    stamped: bool = True
    extra_data: Dict[str, Any] = field(default_factory=dict)

    def copy(self) -> "DocumentInstance":
        """Create an independent copy of this document instance."""
        return DocumentInstance(
            doc_type=self.doc_type,
            owner_name=self.owner_name,
            nationality=self.nationality,
            target_country=self.target_country,
            issue_day=self.issue_day,
            expiry_day=self.expiry_day,
            stamped=self.stamped,
            extra_data=dict(self.extra_data),
        )


@dataclass
class TravelerState:
    """Mutable state representing a traveler or applicant being evaluated by the rules engine."""

    name: str
    origin: str
    destination: str
    current_day: int
    deadline_day: int
    budget: int
    declared_bank_balance: int
    transit_countries: List[str] = field(default_factory=list)
    documents: List[DocumentInstance] = field(default_factory=list)
    action_history: List[str] = field(default_factory=list)

    def copy(self) -> "TravelerState":
        """Create a deep copy of the traveler state for simulation or BFS search."""
        return TravelerState(
            name=self.name,
            origin=self.origin,
            destination=self.destination,
            current_day=self.current_day,
            deadline_day=self.deadline_day,
            budget=self.budget,
            declared_bank_balance=self.declared_bank_balance,
            transit_countries=list(self.transit_countries),
            documents=[d.copy() for d in self.documents],
            action_history=list(self.action_history),
        )

    def get_document(self, doc_type: str, target_country: Optional[str] = None) -> Optional[DocumentInstance]:
        """Find the most recently issued document of a given type (and optional target country)."""
        matches = [
            d
            for d in self.documents
            if d.doc_type == doc_type
            and (target_country is None or not d.target_country or d.target_country == target_country)
        ]
        if not matches:
            return None
        return matches[-1]


@dataclass(frozen=True)
class PortraitSpec:
    """Procedural portrait parameters for an applicant."""

    skin_color: Tuple[int, int, int]
    hair_color: Tuple[int, int, int]
    shirt_color: Tuple[int, int, int]
    hair_style: int
    has_glasses: bool
    has_mustache: bool
    eye_style: int


@dataclass
class ApplicantCase:
    """A generated applicant presenting documents at the consular desk."""

    case_id: int
    name: str
    origin: str
    destination: str
    current_day: int
    transit_countries: List[str]
    declared_bank_balance: int
    documents: List[DocumentInstance]
    portrait: PortraitSpec
    dialogue: str
    is_traveler_callback: bool = False
    expected_decision: str = ""
    expected_reason_code: str = ""

    def to_traveler_state(self) -> TravelerState:
        """Convert this applicant into a TravelerState for unified RuleEngine validation."""
        return TravelerState(
            name=self.name,
            origin=self.origin,
            destination=self.destination,
            current_day=self.current_day,
            deadline_day=self.current_day + 999,
            budget=999,
            declared_bank_balance=self.declared_bank_balance,
            transit_countries=list(self.transit_countries),
            documents=[d.copy() for d in self.documents],
        )


@dataclass(frozen=True)
class TravelerLevelSpec:
    """Specification for a single level in the Traveler campaign."""

    id: int
    title: str
    subtitle: str
    intro_text: str
    goal_text: str
    traveler_name: str
    origin: str
    destination: str
    transit_countries: Tuple[str, ...]
    start_day: int
    deadline_day: int
    start_budget: int
    declared_bank_balance: int
    initial_documents: Tuple[DocumentInstance, ...]
    available_actions: Tuple[str, ...]
    hints: Tuple[str, ...]
    star_thresholds: Dict[str, Dict[str, int]]


@dataclass(frozen=True)
class ConsulShiftSpec:
    """Specification for a single shift in the Consul campaign."""

    id: int
    title: str
    subtitle: str
    destination: str
    current_day: int
    seed: int
    applicant_count: int
    time_limit_seconds: int
    pay_per_correct: int
    penalty_per_wrong: int
    max_strikes: int
    intro_text: str
    active_rules_summary: Tuple[str, ...]
    announcement: str
    active_documents: Tuple[str, ...]
    allowed_error_types: Tuple[str, ...]
    reuse_traveler_mistakes: bool
