"""How to Play screen with illustrated procedural explanations of both campaigns."""

from typing import TYPE_CHECKING

import pygame

from game.constants import (
    COLOR_ACCENT_BLUE,
    COLOR_ACCENT_GOLD,
    COLOR_ACCENT_TEAL,
    COLOR_BG_DARK,
    COLOR_BG_MAIN,
    COLOR_BG_PANEL,
    COLOR_BORDER,
    COLOR_TEXT_MAIN,
    COLOR_TEXT_MUTED,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)
from game.core.models import DocumentInstance, PortraitSpec
from game.ui.drawing import draw_flag, draw_official_seal, draw_star
from game.ui.screens import BaseScreen
from game.ui.theme import draw_text_wrapped
from game.ui.widgets import Button, DocumentCard, Panel

if TYPE_CHECKING:
    from game.app import Game


class HowToPlayScreen(BaseScreen):
    """Illustrated handbook screen explaining Traveler planning, Consul inspection, and the Rules Engine."""

    def __init__(self, app: "Game") -> None:
        super().__init__(app)
        self.back_button = Button(
            pygame.Rect(40, 26, 150, 42),
            "← Main Menu",
            on_click=self._on_back,
            bg_color=COLOR_BG_PANEL,
        )
        self.sample_card: DocumentCard = self._make_sample_card()

    def _make_sample_card(self) -> DocumentCard:
        sample_doc = DocumentInstance(
            doc_type="passport",
            owner_name="Clara Vance",
            nationality="valdoria",
            target_country="",
            issue_day=1,
            expiry_day=60,
            stamped=True,
        )
        sample_portrait = PortraitSpec(
            skin_color=(242, 211, 188),
            hair_color=(112, 74, 46),
            shirt_color=(59, 105, 152),
            hair_style=0,
            has_glasses=True,
            has_mustache=False,
            eye_style=0,
        )
        return DocumentCard(
            rect=pygame.Rect(885, 155, 290, 175),
            doc=sample_doc,
            doc_spec=self.app.db.documents["passport"],
            countries=self.app.db.countries,
            portrait=sample_portrait,
            interactive_fields=False,
        )

    def _on_back(self) -> None:
        self.app.audio.play("click")
        self.app.change_screen("menu")

    def handle_event(self, event: pygame.event.Event) -> None:
        """Handle mouse click on Back button or Esc key."""
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._on_back()
            return
        self.back_button.handle_event(event)

    def update(self, dt: float) -> None:
        """Update button hover state."""
        self.back_button.update(dt)

    def draw(self, surface: pygame.Surface) -> None:
        """Render the 3 illustrated guide columns."""
        surface.fill(COLOR_BG_MAIN)
        self.back_button.draw(surface, self.app.fonts)

        f_hdr = self.app.fonts.get(30, bold=True)
        f_sec = self.app.fonts.get(18, bold=True)
        f_body = self.app.fonts.get(14)
        f_mono = self.app.fonts.get(12, bold=True, mono=True)

        title_s = f_hdr.render("HOW TO PLAY — BUREAU OF MOBILITY HANDBOOK", True, COLOR_ACCENT_GOLD)
        surface.blit(title_s, (SCREEN_WIDTH // 2 - title_s.get_width() // 2, 30))

        # Column 1: Traveler Campaign
        col1 = Panel(pygame.Rect(36, 95, 385, 585), title="1. TRAVELER CAMPAIGN (PLANNING)")
        col1.draw(surface, self.app.fonts)

        t_points = [
            "• GOAL: Collect all required entry documents and depart before the Deadline Day without running out of Budget.",
            "• PASSPORT BUFFER: Countries require your passport to remain valid for N days BEYOND your arrival day (e.g., Norwen requires 30+ days past arrival). If your passport expires too soon, renew it first!",
            "• PREREQUISITES: Some countries (like Keshmar & Sunmere) require an Invitation Letter BEFORE you can apply for an Entry Visa.",
            "• TRANSIT PERMITS: If your route crosses a transit hub like Tavik, you must obtain a Tavik Transit Permit.",
            "• STAR RATING: Earn up to 3 Stars by finishing quickly with spare money.",
        ]
        y = 148
        for pt in t_points:
            y = draw_text_wrapped(
                surface,
                pt,
                f_body,
                COLOR_TEXT_MAIN,
                pygame.Rect(54, y, 348, 95),
                line_spacing=4,
            )
            y += 12

        for i in range(3):
            draw_star(surface, (165 + i * 48, 632), 16, True)

        # Column 2: Consul Campaign
        col2 = Panel(pygame.Rect(446, 95, 385, 585), title="2. CONSUL CAMPAIGN (INSPECTION)")
        col2.draw(surface, self.app.fonts)

        c_points = [
            "• UNLOCK: Complete the first 3 Traveler levels (or run with --unlock-all) to unlock the Consular Desk.",
            "• RULEBOOK [Tab]: Check today's Current Day, destination rules, passport validity buffer, and Visa-Free diplomatic nations.",
            "• FLAG DISCREPANCIES: Click suspicious fields on paper cards (holder name, expiry date, destination country, bank balance, or missing seal) to highlight them.",
            "• THREE VERDICTS:\n  1. APPROVE: All required documents are present and valid.\n  2. DENY: A document is expired, forged, unstamped, wrong country, or low funds.\n  3. REQUEST MISSING DOC: A required document is missing from the desk.",
            "• STRIKES: Wrong verdicts cost a Strike. 3 Strikes fail the shift!",
        ]
        y = 148
        for pt in c_points:
            y = draw_text_wrapped(
                surface,
                pt,
                f_body,
                COLOR_TEXT_MAIN,
                pygame.Rect(464, y, 348, 120),
                line_spacing=4,
            )
            y += 10

        # Column 3: Anatomy of a Document & Shortcuts
        col3 = Panel(pygame.Rect(856, 95, 388, 585), title="3. DOCUMENT ANATOMY & CONTROLS")
        col3.draw(surface, self.app.fonts)

        self.sample_card.draw(surface, self.app.fonts, current_day=10)

        anat_text = (
            "Above is a sample Valdoria Passport:\n"
            "• Check Holder Name against the applicant.\n"
            "• Check Expires Day against Today + Buffer.\n"
            "• Verify the circular Bureau Seal in the corner."
        )
        draw_text_wrapped(
            surface,
            anat_text,
            f_body,
            COLOR_TEXT_MUTED,
            pygame.Rect(876, 345, 348, 100),
            line_spacing=4,
        )

        # Keyboard shortcuts box
        kb_box = pygame.Rect(874, 445, 352, 215)
        pygame.draw.rect(surface, COLOR_BG_DARK, kb_box, border_radius=8)
        pygame.draw.rect(surface, COLOR_BORDER, kb_box, width=1, border_radius=8)

        kb_hdr = f_sec.render("KEYBOARD SHORTCUTS", True, COLOR_ACCENT_TEAL)
        surface.blit(kb_hdr, (kb_box.x + 16, kb_box.y + 12))

        shortcuts = [
            ("Left Click", "Interact / Flag Discrepancy"),
            ("Esc", "Pause Menu / Back"),
            ("R", "Instant Restart Level / Shift"),
            ("H", "Reveal Hint (Traveler Mode)"),
            ("Tab", "Toggle Consular Rulebook"),
            ("M", "Mute / Unmute Audio"),
            ("F11", "Toggle Fullscreen"),
        ]
        sy = kb_box.y + 44
        for key_str, desc_str in shortcuts:
            ks = f_mono.render(f"[{key_str}]", True, COLOR_ACCENT_GOLD)
            ds = f_body.render(desc_str, True, COLOR_TEXT_MAIN)
            surface.blit(ks, (kb_box.x + 16, sy))
            surface.blit(ds, (kb_box.x + 122, sy - 1))
            sy += 23
