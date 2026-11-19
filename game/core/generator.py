"""Deterministic seeded applicant and document generator for the Consul campaign."""

import random
from typing import List, Optional, Tuple

from game.constants import (
    DECISION_APPROVE,
    DECISION_DENY,
    DECISION_REQUEST_DOC,
    REASON_EXPIRED,
    REASON_INSUFFICIENT_FUNDS,
    REASON_INSUFFICIENT_VALIDITY,
    REASON_MISSING_DOC,
    REASON_MISSING_PREREQUISITE,
    REASON_MISSING_STAMP,
    REASON_VALID,
    REASON_WRONG_COUNTRY,
    REASON_WRONG_NAME,
)
from game.core.models import (
    ApplicantCase,
    ConsulShiftSpec,
    DocumentInstance,
    PortraitSpec,
)
from game.core.rules import RuleEngine

FIRST_NAMES: Tuple[str, ...] = (
    "Lukas",
    "Mirela",
    "Henrik",
    "Anja",
    "Dorian",
    "Nadia",
    "Viktor",
    "Selene",
    "Tomas",
    "Klara",
    "Emil",
    "Sora",
    "Gideon",
    "Vera",
    "Bastian",
    "Elena",
)

LAST_NAMES: Tuple[str, ...] = (
    "Kovacs",
    "Lindholm",
    "Vance",
    "Morozov",
    "Alverez",
    "Thorne",
    "Bellerose",
    "Varga",
    "Solberg",
    "Mercer",
    "Halvorsen",
    "Kaspar",
    "Rostova",
    "Sterling",
    "Pendelton",
)

FORGED_FIRST_NAMES: Tuple[str, ...] = (
    "Lukaz",
    "Mirella",
    "Hendrik",
    "Anya",
    "Doryan",
    "Nadya",
    "Victor",
    "Selina",
    "Thomas",
    "Clara",
)

SKIN_TONES: Tuple[Tuple[int, int, int], ...] = (
    (242, 211, 188),
    (229, 188, 154),
    (198, 148, 110),
    (158, 108, 76),
    (247, 224, 206),
)

HAIR_COLORS: Tuple[Tuple[int, int, int], ...] = (
    (45, 38, 34),
    (112, 74, 46),
    (184, 138, 78),
    (145, 62, 42),
    (82, 88, 98),
)

SHIRT_COLORS: Tuple[Tuple[int, int, int], ...] = (
    (59, 105, 152),
    (148, 58, 62),
    (56, 128, 104),
    (118, 88, 152),
    (184, 128, 56),
    (72, 84, 102),
)

GREETINGS: Tuple[str, ...] = (
    "Good day, Officer. All my paperwork should be in order.",
    "Hello! Please process my entry dossier quickly, my train leaves soon.",
    "Greetings from across the border. Here are my travel documents.",
    "Morning, Consul. The agency assured me every stamp is authentic!",
    "Good afternoon. I double-checked the dates myself... mostly.",
)


class ApplicantGenerator:
    """Generates deterministic, rule-verified applicant queues for Consul shifts."""

    def __init__(self, engine: RuleEngine) -> None:
        """Initialize the generator with a shared RuleEngine instance."""
        self.engine = engine

    def generate_shift_queue(
        self,
        shift: ConsulShiftSpec,
        seed_override: Optional[int] = None,
    ) -> List[ApplicantCase]:
        """Generate a deterministic list of ApplicantCase objects for the given shift.

        Every case is verified against self.engine.validate() to guarantee an unambiguous
        expected decision and primary reason code.
        """
        rng = random.Random(seed_override if seed_override is not None else shift.seed)
        cases: List[ApplicantCase] = []
        dest_id = shift.destination
        other_countries = [cid for cid in self.engine.countries if cid != dest_id]

        # Build a deterministic plan of case types (mix of valid, errors, and traveler callbacks)
        error_pool = list(shift.allowed_error_types)
        for idx in range(shift.applicant_count):
            case_id = idx + 1
            # Roughly 40% valid cases, 60% single clear error cases
            is_valid_target = (idx % 3 == 0)
            is_callback = False
            chosen_error = REASON_VALID

            if not is_valid_target and error_pool:
                # In later shifts, inject classic Traveler campaign mistakes for callback flavor
                if shift.reuse_traveler_mistakes and idx == shift.applicant_count - 2:
                    is_callback = True
                    chosen_error = self._pick_traveler_callback_error(shift)
                else:
                    chosen_error = error_pool[(idx + shift.id) % len(error_pool)]

            case = self._build_single_case(
                rng=rng,
                case_id=case_id,
                shift=shift,
                other_countries=other_countries,
                target_error=chosen_error,
                is_callback=is_callback,
            )
            cases.append(case)

        return cases

    def _pick_traveler_callback_error(self, shift: ConsulShiftSpec) -> str:
        """Select a signature mistake reminiscent of Traveler levels 2-5."""
        if REASON_INSUFFICIENT_VALIDITY in shift.allowed_error_types and shift.id == 2:
            return REASON_INSUFFICIENT_VALIDITY
        if REASON_INSUFFICIENT_FUNDS in shift.allowed_error_types and shift.id == 3:
            return REASON_INSUFFICIENT_FUNDS
        if REASON_MISSING_PREREQUISITE in shift.allowed_error_types and shift.id == 4:
            return REASON_MISSING_PREREQUISITE
        if REASON_INSUFFICIENT_VALIDITY in shift.allowed_error_types:
            return REASON_INSUFFICIENT_VALIDITY
        return shift.allowed_error_types[0]

    def _build_single_case(
        self,
        rng: random.Random,
        case_id: int,
        shift: ConsulShiftSpec,
        other_countries: List[str],
        target_error: str,
        is_callback: bool,
    ) -> ApplicantCase:
        """Construct a valid baseline applicant and inject at most one controlled discrepancy."""
        dest_spec = self.engine.countries[shift.destination]
        day = shift.current_day

        # Pick applicant name & origin
        if is_callback:
            name, origin, dialogue = self._get_callback_persona(shift, target_error, other_countries, rng)
        else:
            first = rng.choice(FIRST_NAMES)
            last = rng.choice(LAST_NAMES)
            name = f"{first} {last}"
            # If error requires a visa (e.g. wrong_country or missing_prerequisite), ensure non-visa-free origin
            non_vf_origins = [c for c in other_countries if not dest_spec.is_visa_free_for(c)]
            if target_error in (REASON_WRONG_COUNTRY, REASON_MISSING_PREREQUISITE) and non_vf_origins:
                origin = rng.choice(non_vf_origins)
            else:
                origin = rng.choice(other_countries)
            dialogue = rng.choice(GREETINGS)

        # Determine if applicant transited through Tavik
        transit_countries: List[str] = []
        if "transit_permit" in shift.active_documents and origin != "tavik" and shift.destination != "tavik":
            if is_callback or rng.random() < 0.45:
                transit_countries = ["tavik"]

        # Required baseline balance
        min_bal = max(dest_spec.min_bank_balance, 200)
        declared_balance = min_bal + rng.randint(40, 220)

        # Build a 100% valid document set first
        req_docs = self.engine.get_required_documents(
            origin=origin,
            destination=shift.destination,
            transit_countries=transit_countries,
            active_doc_filter=shift.active_documents,
        )

        # Also include prerequisite documents if visa is present and prerequisite is in active_documents
        req_doc_types = [r[0] for r in req_docs]
        if "visa" in req_doc_types:
            for prereq_id in dest_spec.visa_prerequisites:
                if (
                    prereq_id in shift.active_documents
                    and prereq_id not in req_doc_types
                ):
                    p_spec = self.engine.documents[prereq_id]
                    t_country = shift.destination if p_spec.target_country_specific else ""
                    req_docs.append((prereq_id, t_country))

        docs: List[DocumentInstance] = []
        for doc_type, expected_target in req_docs:
            doc_spec = self.engine.documents[doc_type]
            issue_day = max(1, day - rng.randint(2, 8))
            if doc_type == "passport":
                expiry_day = day + dest_spec.passport_min_validity_days + rng.randint(10, 35)
            else:
                expiry_day = day + rng.randint(8, max(10, doc_spec.validity_days))
            extra = {}
            if doc_type == "bank_statement":
                extra["balance"] = declared_balance
            docs.append(
                DocumentInstance(
                    doc_type=doc_type,
                    owner_name=name,
                    nationality=origin,
                    target_country=expected_target,
                    issue_day=issue_day,
                    expiry_day=expiry_day,
                    stamped=True,
                    extra_data=extra,
                )
            )

        # Now inject the exact target error if not REASON_VALID
        if target_error != REASON_VALID:
            self._inject_error(
                rng=rng,
                docs=docs,
                target_error=target_error,
                shift=shift,
                origin=origin,
                other_countries=other_countries,
            )

        portrait = PortraitSpec(
            skin_color=rng.choice(SKIN_TONES),
            hair_color=rng.choice(HAIR_COLORS),
            shirt_color=rng.choice(SHIRT_COLORS),
            hair_style=rng.randint(0, 3),
            has_glasses=rng.random() < 0.35,
            has_mustache=rng.random() < 0.25,
            eye_style=rng.randint(0, 2),
        )

        case = ApplicantCase(
            case_id=case_id,
            name=name,
            origin=origin,
            destination=shift.destination,
            current_day=day,
            transit_countries=transit_countries,
            declared_bank_balance=declared_balance,
            documents=docs,
            portrait=portrait,
            dialogue=dialogue,
            is_traveler_callback=is_callback,
        )

        # Validate with RuleEngine to stamp authoritative expected decision & reason
        result = self.engine.validate(
            case.to_traveler_state(),
            destination=shift.destination,
            date=day,
            active_doc_filter=shift.active_documents,
        )
        case.expected_decision = result.expected_consul_decision
        case.expected_reason_code = result.primary_code
        return case

    def _get_callback_persona(
        self,
        shift: ConsulShiftSpec,
        target_error: str,
        other_countries: List[str],
        rng: random.Random,
    ) -> Tuple[str, str, str]:
        """Return a nostalgic persona referencing Traveler campaign mistakes."""
        dest_spec = self.engine.countries[shift.destination]
        non_vf = [c for c in other_countries if not dest_spec.is_visa_free_for(c)]
        origin = "valdoria" if "valdoria" in non_vf else (non_vf[0] if non_vf else other_countries[0])

        if target_error == REASON_INSUFFICIENT_VALIDITY:
            return (
                "Arthur Pendelton",
                origin,
                "My passport still has two weeks left before it expires! Surely that's enough?",
            )
        if target_error == REASON_INSUFFICIENT_FUNDS:
            return (
                "Marcus Sterling",
                origin,
                "I spent all my spare cash on agency fees... don't look too closely at my bank balance!",
            )
        if target_error == REASON_MISSING_PREREQUISITE:
            return (
                "Sonia Lindqvist",
                origin,
                "I got the Entry Visa stamped, though I left my Invitation Letter back home.",
            )
        return (
            "Elena Rostova",
            origin,
            "The travel agency was in such a rush they might have forgotten a stamp or date!",
        )

    def _inject_error(
        self,
        rng: random.Random,
        docs: List[DocumentInstance],
        target_error: str,
        shift: ConsulShiftSpec,
        origin: str,
        other_countries: List[str],
    ) -> None:
        """Mutate docs in-place to create a single clear rule violation of type target_error."""
        day = shift.current_day
        dest_spec = self.engine.countries[shift.destination]

        if target_error == REASON_MISSING_DOC:
            # Remove a required non-passport document if possible, otherwise remove passport
            non_pass = [d for d in docs if d.doc_type != "passport"]
            victim = rng.choice(non_pass) if non_pass else docs[0]
            docs.remove(victim)
            return

        if target_error == REASON_INSUFFICIENT_VALIDITY:
            p_doc = next((d for d in docs if d.doc_type == "passport"), docs[0])
            # Valid on arrival day, but less than passport_min_validity_days
            shortfall = rng.randint(5, max(6, dest_spec.passport_min_validity_days - 4))
            p_doc.expiry_day = day + shortfall
            return

        if target_error == REASON_EXPIRED:
            victim = rng.choice(docs)
            victim.expiry_day = day - rng.randint(1, 6)
            return

        if target_error == REASON_WRONG_NAME:
            victim = rng.choice(docs)
            parts = victim.owner_name.split(" ")
            wrong_first = rng.choice([n for n in FORGED_FIRST_NAMES if n != parts[0]])
            victim.owner_name = f"{wrong_first} {parts[-1]}"
            return

        if target_error == REASON_MISSING_STAMP:
            victim = rng.choice(docs)
            victim.stamped = False
            return

        if target_error == REASON_WRONG_COUNTRY:
            country_docs = [
                d
                for d in docs
                if self.engine.documents[d.doc_type].target_country_specific
            ]
            if country_docs:
                victim = rng.choice(country_docs)
                wrong_targets = [
                    cid
                    for cid in self.engine.countries
                    if cid != victim.target_country and cid != origin
                ]
                victim.target_country = rng.choice(wrong_targets) if wrong_targets else other_countries[0]
            else:
                docs[0].expiry_day = day - 2
            return

        if target_error == REASON_INSUFFICIENT_FUNDS:
            b_doc = next((d for d in docs if d.doc_type == "bank_statement"), None)
            if b_doc and dest_spec.min_bank_balance > 0:
                b_doc.extra_data["balance"] = max(20, dest_spec.min_bank_balance - rng.randint(35, 90))
            else:
                docs[0].stamped = False
            return

        if target_error == REASON_MISSING_PREREQUISITE:
            inv_doc = next((d for d in docs if d.doc_type == "invitation_letter"), None)
            if inv_doc:
                docs.remove(inv_doc)
            else:
                docs[0].stamped = False
            return
