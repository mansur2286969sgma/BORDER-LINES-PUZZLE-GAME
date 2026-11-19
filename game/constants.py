"""Centralized constants, tunable numbers, and color palette for BORDER LINES."""

from typing import Dict, Tuple

Color = Tuple[int, int, int]

# Window & display settings
GAME_TITLE: str = "BORDER LINES"
GAME_SUBTITLE: str = "A Bureaucratic Logic Puzzle of Visas & Borders"
SCREEN_WIDTH: int = 1280
SCREEN_HEIGHT: int = 720
FPS: int = 60

# Campaign unlock rule
CONSUL_UNLOCK_TRAVELER_LEVELS: int = 3
MAX_STRIKES_DEFAULT: int = 3

# Audio settings
AUDIO_SAMPLE_RATE: int = 22050
DEFAULT_SFX_VOLUME: float = 0.65
DEFAULT_MUSIC_VOLUME: float = 0.35

# Modern flat color palette
COLOR_BG_DARK: Color = (22, 28, 38)
COLOR_BG_MAIN: Color = (30, 38, 52)
COLOR_BG_PANEL: Color = (41, 51, 69)
COLOR_BG_PANEL_ALT: Color = (50, 62, 82)
COLOR_BG_CARD: Color = (247, 243, 232)
COLOR_BG_CARD_ALT: Color = (238, 232, 216)
COLOR_DESK_WOOD: Color = (72, 52, 42)
COLOR_DESK_MAT: Color = (45, 72, 66)

COLOR_TEXT_MAIN: Color = (240, 244, 248)
COLOR_TEXT_MUTED: Color = (165, 178, 198)
COLOR_TEXT_DARK: Color = (35, 42, 54)
COLOR_TEXT_INK: Color = (28, 45, 78)

COLOR_ACCENT_BLUE: Color = (66, 153, 225)
COLOR_ACCENT_GOLD: Color = (236, 201, 75)
COLOR_ACCENT_TEAL: Color = (56, 178, 172)
COLOR_ACCENT_ORANGE: Color = (237, 137, 54)
COLOR_ACCENT_PURPLE: Color = (159, 122, 234)

COLOR_SUCCESS: Color = (72, 187, 120)
COLOR_SUCCESS_DARK: Color = (39, 103, 73)
COLOR_WARNING: Color = (236, 201, 75)
COLOR_DANGER: Color = (229, 62, 62)
COLOR_DANGER_DARK: Color = (155, 44, 44)

COLOR_BORDER: Color = (74, 88, 112)
COLOR_SHADOW: Color = (12, 16, 23)

# Document accent header colors
DOC_HEADER_COLORS: Dict[str, Color] = {
    "passport": (44, 82, 130),
    "visa": (155, 44, 44),
    "invitation_letter": (116, 66, 168),
    "bank_statement": (47, 133, 90),
    "vaccination_certificate": (214, 158, 46),
    "travel_insurance": (49, 151, 149),
    "transit_permit": (192, 86, 33),
}

# Canonical denial reason codes used in the Rules Engine and Consul Campaign
REASON_VALID: str = "valid"
REASON_MISSING_DOC: str = "missing_doc"
REASON_EXPIRED: str = "expired"
REASON_INSUFFICIENT_VALIDITY: str = "insufficient_validity"
REASON_WRONG_NAME: str = "wrong_name"
REASON_WRONG_COUNTRY: str = "wrong_country"
REASON_MISSING_STAMP: str = "missing_stamp"
REASON_INSUFFICIENT_FUNDS: str = "insufficient_funds"
REASON_MISSING_PREREQUISITE: str = "missing_prerequisite"
REASON_DEADLINE_PASSED: str = "deadline_passed"
REASON_OVER_BUDGET: str = "over_budget"

DENIAL_REASON_LABELS: Dict[str, str] = {
    REASON_EXPIRED: "Document Expired",
    REASON_INSUFFICIENT_VALIDITY: "Passport Validity Too Short",
    REASON_WRONG_NAME: "Name Mismatch / Forgery",
    REASON_WRONG_COUNTRY: "Wrong Destination / Target Country",
    REASON_MISSING_STAMP: "Missing Official Stamp",
    REASON_INSUFFICIENT_FUNDS: "Insufficient Bank Balance",
    REASON_MISSING_PREREQUISITE: "Missing Visa Prerequisite (Invitation)",
    REASON_MISSING_DOC: "Missing Required Document",
}

# Consul decision types
DECISION_APPROVE: str = "APPROVE"
DECISION_DENY: str = "DENY"
DECISION_REQUEST_DOC: str = "REQUEST_MISSING_DOCUMENT"
