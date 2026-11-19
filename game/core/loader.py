"""JSON data loader and schema validator for BORDER LINES."""

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from game.core.models import (
    ConsulShiftSpec,
    CountrySpec,
    DocumentInstance,
    DocumentSpec,
    FlagSpec,
    TravelerLevelSpec,
)


class DataLoadError(Exception):
    """Raised when a JSON data file is missing, malformed, or fails schema validation."""


@dataclass(frozen=True)
class GameDatabase:
    """Immutable container holding all loaded and validated JSON content."""

    countries: Dict[str, CountrySpec]
    documents: Dict[str, DocumentSpec]
    traveler_levels: List[TravelerLevelSpec]
    consul_shifts: List[ConsulShiftSpec]


def _require_fields(obj: Dict[str, Any], required: List[str], context: str) -> None:
    """Ensure all required keys exist in a dictionary, raising a descriptive DataLoadError if not."""
    if not isinstance(obj, dict):
        raise DataLoadError(f"{context}: Expected a JSON object, got {type(obj).__name__}.")
    missing = [k for k in required if k not in obj]
    if missing:
        raise DataLoadError(f"{context}: Missing required field(s): {', '.join(missing)}.")


def _load_json_file(path: str) -> Dict[str, Any]:
    """Read and parse a JSON file with clear error reporting."""
    if not os.path.isfile(path):
        raise DataLoadError(f"Data file not found: '{path}'.")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        raise DataLoadError(
            f"Malformed JSON in '{path}' at line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc
    except OSError as exc:
        raise DataLoadError(f"Could not read '{path}': {exc}") from exc

    if not isinstance(data, dict):
        raise DataLoadError(f"Top-level JSON structure in '{path}' must be an object.")
    return data


def load_countries(path: str) -> Dict[str, CountrySpec]:
    """Load and validate countries.json."""
    raw = _load_json_file(path)
    _require_fields(raw, ["countries"], path)
    if not isinstance(raw["countries"], list) or not raw["countries"]:
        raise DataLoadError(f"{path}: 'countries' must be a non-empty list.")

    countries: Dict[str, CountrySpec] = {}
    req_keys = [
        "id",
        "name",
        "motto",
        "description",
        "map_pos",
        "flag",
        "visa_processing_days",
        "visa_fee",
        "passport_min_validity_days",
        "min_bank_balance",
        "required_documents",
        "visa_prerequisites",
        "relations",
    ]
    for idx, item in enumerate(raw["countries"]):
        ctx = f"{path} -> countries[{idx}]"
        _require_fields(item, req_keys, ctx)
        flag_raw = item["flag"]
        _require_fields(flag_raw, ["style", "colors"], f"{ctx}.flag")
        colors: Tuple[Tuple[int, int, int], ...] = tuple(
            (int(c[0]), int(c[1]), int(c[2])) for c in flag_raw["colors"]
        )
        emblem_col = flag_raw.get("emblem_color", [255, 255, 255])
        flag = FlagSpec(
            style=str(flag_raw["style"]),
            colors=colors,
            emblem=str(flag_raw.get("emblem", "none")),
            emblem_color=(int(emblem_col[0]), int(emblem_col[1]), int(emblem_col[2])),
        )
        pos = item["map_pos"]
        country = CountrySpec(
            id=str(item["id"]),
            name=str(item["name"]),
            motto=str(item["motto"]),
            description=str(item["description"]),
            map_pos=(int(pos[0]), int(pos[1])),
            flag=flag,
            visa_processing_days=int(item["visa_processing_days"]),
            visa_fee=int(item["visa_fee"]),
            passport_min_validity_days=int(item["passport_min_validity_days"]),
            min_bank_balance=int(item["min_bank_balance"]),
            required_documents=tuple(str(x) for x in item["required_documents"]),
            visa_prerequisites=tuple(str(x) for x in item["visa_prerequisites"]),
            relations={str(k): str(v) for k, v in dict(item["relations"]).items()},
        )
        countries[country.id] = country
    return countries


def load_documents(path: str) -> Dict[str, DocumentSpec]:
    """Load and validate documents.json."""
    raw = _load_json_file(path)
    _require_fields(raw, ["documents"], path)
    if not isinstance(raw["documents"], list) or not raw["documents"]:
        raise DataLoadError(f"{path}: 'documents' must be a non-empty list.")

    docs: Dict[str, DocumentSpec] = {}
    req_keys = [
        "id",
        "name",
        "short_name",
        "issuer",
        "action_label",
        "description",
        "validity_days",
        "processing_days",
        "cost",
        "prerequisites",
        "requires_stamp",
        "target_country_specific",
        "common_errors",
    ]
    for idx, item in enumerate(raw["documents"]):
        ctx = f"{path} -> documents[{idx}]"
        _require_fields(item, req_keys, ctx)
        doc = DocumentSpec(
            id=str(item["id"]),
            name=str(item["name"]),
            short_name=str(item["short_name"]),
            issuer=str(item["issuer"]),
            action_label=str(item["action_label"]),
            description=str(item["description"]),
            validity_days=int(item["validity_days"]),
            processing_days=int(item["processing_days"]),
            cost=int(item["cost"]),
            prerequisites=tuple(str(x) for x in item["prerequisites"]),
            requires_stamp=bool(item["requires_stamp"]),
            target_country_specific=bool(item["target_country_specific"]),
            common_errors=tuple(str(x) for x in item["common_errors"]),
        )
        docs[doc.id] = doc
    return docs


def load_traveler_levels(
    path: str,
    countries: Dict[str, CountrySpec],
    documents: Dict[str, DocumentSpec],
) -> List[TravelerLevelSpec]:
    """Load and validate traveler_levels.json against loaded countries and documents."""
    raw = _load_json_file(path)
    _require_fields(raw, ["levels"], path)
    if not isinstance(raw["levels"], list) or not raw["levels"]:
        raise DataLoadError(f"{path}: 'levels' must be a non-empty list.")

    levels: List[TravelerLevelSpec] = []
    req_keys = [
        "id",
        "title",
        "subtitle",
        "intro_text",
        "goal_text",
        "traveler_name",
        "origin",
        "destination",
        "transit_countries",
        "start_day",
        "deadline_day",
        "start_budget",
        "declared_bank_balance",
        "initial_documents",
        "available_actions",
        "hints",
        "star_thresholds",
    ]
    for idx, item in enumerate(raw["levels"]):
        ctx = f"{path} -> levels[{idx}]"
        _require_fields(item, req_keys, ctx)
        origin = str(item["origin"])
        dest = str(item["destination"])
        if origin not in countries:
            raise DataLoadError(f"{ctx}: Unknown origin country '{origin}'.")
        if dest not in countries:
            raise DataLoadError(f"{ctx}: Unknown destination country '{dest}'.")

        init_docs: List[DocumentInstance] = []
        for d_idx, d_raw in enumerate(item["initial_documents"]):
            d_ctx = f"{ctx}.initial_documents[{d_idx}]"
            _require_fields(
                d_raw,
                ["doc_type", "owner_name", "nationality", "target_country", "issue_day", "expiry_day", "stamped"],
                d_ctx,
            )
            dtype = str(d_raw["doc_type"])
            if dtype not in documents:
                raise DataLoadError(f"{d_ctx}: Unknown document type '{dtype}'.")
            init_docs.append(
                DocumentInstance(
                    doc_type=dtype,
                    owner_name=str(d_raw["owner_name"]),
                    nationality=str(d_raw["nationality"]),
                    target_country=str(d_raw["target_country"]),
                    issue_day=int(d_raw["issue_day"]),
                    expiry_day=int(d_raw["expiry_day"]),
                    stamped=bool(d_raw["stamped"]),
                    extra_data=dict(d_raw.get("extra_data", {})),
                )
            )

        levels.append(
            TravelerLevelSpec(
                id=int(item["id"]),
                title=str(item["title"]),
                subtitle=str(item["subtitle"]),
                intro_text=str(item["intro_text"]),
                goal_text=str(item["goal_text"]),
                traveler_name=str(item["traveler_name"]),
                origin=origin,
                destination=dest,
                transit_countries=tuple(str(c) for c in item["transit_countries"]),
                start_day=int(item["start_day"]),
                deadline_day=int(item["deadline_day"]),
                start_budget=int(item["start_budget"]),
                declared_bank_balance=int(item["declared_bank_balance"]),
                initial_documents=tuple(init_docs),
                available_actions=tuple(str(a) for a in item["available_actions"]),
                hints=tuple(str(h) for h in item["hints"]),
                star_thresholds=dict(item["star_thresholds"]),
            )
        )
    return levels


def load_consul_shifts(
    path: str,
    countries: Dict[str, CountrySpec],
    documents: Dict[str, DocumentSpec],
) -> List[ConsulShiftSpec]:
    """Load and validate consul_shifts.json against loaded countries and documents."""
    raw = _load_json_file(path)
    _require_fields(raw, ["shifts"], path)
    if not isinstance(raw["shifts"], list) or not raw["shifts"]:
        raise DataLoadError(f"{path}: 'shifts' must be a non-empty list.")

    shifts: List[ConsulShiftSpec] = []
    req_keys = [
        "id",
        "title",
        "subtitle",
        "destination",
        "current_day",
        "seed",
        "applicant_count",
        "time_limit_seconds",
        "pay_per_correct",
        "penalty_per_wrong",
        "max_strikes",
        "intro_text",
        "active_rules_summary",
        "announcement",
        "active_documents",
        "allowed_error_types",
        "reuse_traveler_mistakes",
    ]
    for idx, item in enumerate(raw["shifts"]):
        ctx = f"{path} -> shifts[{idx}]"
        _require_fields(item, req_keys, ctx)
        dest = str(item["destination"])
        if dest not in countries:
            raise DataLoadError(f"{ctx}: Unknown destination country '{dest}'.")
        for doc_id in item["active_documents"]:
            if doc_id not in documents:
                raise DataLoadError(f"{ctx}: Unknown active document '{doc_id}'.")

        shifts.append(
            ConsulShiftSpec(
                id=int(item["id"]),
                title=str(item["title"]),
                subtitle=str(item["subtitle"]),
                destination=dest,
                current_day=int(item["current_day"]),
                seed=int(item["seed"]),
                applicant_count=int(item["applicant_count"]),
                time_limit_seconds=int(item["time_limit_seconds"]),
                pay_per_correct=int(item["pay_per_correct"]),
                penalty_per_wrong=int(item["penalty_per_wrong"]),
                max_strikes=int(item["max_strikes"]),
                intro_text=str(item["intro_text"]),
                active_rules_summary=tuple(str(s) for s in item["active_rules_summary"]),
                announcement=str(item["announcement"]),
                active_documents=tuple(str(d) for d in item["active_documents"]),
                allowed_error_types=tuple(str(e) for e in item["allowed_error_types"]),
                reuse_traveler_mistakes=bool(item["reuse_traveler_mistakes"]),
            )
        )
    return shifts


def load_game_database(data_dir: str) -> GameDatabase:
    """Load all JSON files from data_dir and return a validated GameDatabase."""
    countries = load_countries(os.path.join(data_dir, "countries.json"))
    documents = load_documents(os.path.join(data_dir, "documents.json"))
    traveler_levels = load_traveler_levels(
        os.path.join(data_dir, "traveler_levels.json"), countries, documents
    )
    consul_shifts = load_consul_shifts(
        os.path.join(data_dir, "consul_shifts.json"), countries, documents
    )
    return GameDatabase(
        countries=countries,
        documents=documents,
        traveler_levels=traveler_levels,
        consul_shifts=consul_shifts,
    )
