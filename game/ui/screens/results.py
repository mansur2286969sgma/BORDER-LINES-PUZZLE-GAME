"""Results screen for both Traveler and Consul campaigns with star rating,confetti, and rule reports."""

from typing import List, Optional, TYPE_CHECKING

import pygame

from game.campaigns.consul import ConsulSession
from game.campaigns.traveler import TravelerSession
from game.constants import (
    COLOR_ACCENT_BLUE,
    COLOR_ACCENT_GOLD,
    COLOR_ACCENT_TEAL,
    COLOR_BG_DARK,
    COLOR_BG_MAIN,
    COLOR_BG_PANEL,
    COLOR_BORDER,
    COLOR_DANGER,
    COLOR_SUCCESS,
    COLOR_SUCCESS_DARK,
    COLOR_TEXT_MAIN,
    COLOR_TEXT_MUTED,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)
from game.ui.drawing import draw_star
from game.ui.effects import ParticleSystem
from game.ui.screens import BaseScreen
from game.ui.theme import draw_text_wrapped
from game.ui.widgets import Button, Panel

if TYPE_CHECKING:
    from game.app import Game


class ResultsScreen(BaseScreen):
    """End-of-level / end-of-shift results summary with stars, reasons report, and next/retry actions."""

    def __init__(self, app: "Game") -> None:
        super().__init__(app)
        self.mode: str = "traveler"
        self.traveler_session: Optional[TravelerSession] = None
        self.consul_session: Optional[ConsulSession] = None
        self.buttons: List[Button] = []
        self.particles = ParticleSystem()

    def set_traveler_result(self, session: TravelerSession) -> None:
        """Configure results screen for a finished Traveler level."""
        self.mode = "traveler"
        self.traveler_session = session
        self.consul_session = None
        self.particles.clear()
        if session.won:
            self.particles.spawn_confetti(SCREEN_WIDTH // 2, 180, count=60)
        self._build_buttons()

    def set_consul_result(self, session: ConsulSession) -> None:
        """Configure results screen for a finished Consul shift."""
        self.mode = "consul"
        self.consul_session = session
        self.traveler_session = None
        self.particles.clear()
        if session.won:
            self.particles.spawn_confetti(SCREEN_WIDTH // 2, 180, count=60)
        self._build_buttons()

    def _build_buttons(self) -> None:
        self.buttons.clear()
        cx = SCREEN_WIDTH // 2
        y = 585

        self.buttons.append(
            Button(
                pygame.Rect(cx - 310, y, 190, 48),
                "RETRY [R]",
                on_click=self._on_retry,
                bg_color=COLOR_ACCENT_BLUE,
            )
        )

        # Next level/shift button if won and next exists
        has_next = False
        if self.mode == "traveler" and self.traveler_session and self.traveler_session.won:
            has_next = self.traveler_session.level.id < len(self.app.db.traveler_levels)
        elif self.mode == "consul" and self.consul_session and self.consul_session.won:
            has_next = self.consul_session.shift.id < len(self.app.db.consul_shifts)

        self.buttons.append(
            Button(
                pygame.Rect(cx - 95, y, 190, 48),
                "NEXT LEVEL" if self.mode == "traveler" else "NEXT SHIFT",
                on_click=self._on_next,
                bg_color=COLOR_SUCCESS_DARK,
                enabled=has_next,
            )
        )

        self.buttons.append(
            Button(
                pygame.Rect(cx + 120, y, 190, 48),
                "LEVEL SELECT",
                on_click=self._on_select,
                bg_color=COLOR_BG_PANEL,
            )
        )

    def _on_retry(self) -> None:
        self.app.audio.play("click")
        if self.mode == "traveler" and self.traveler_session:
            self.app.start_traveler_level(self.traveler_session.level.id)
        elif self.mode == "consul" and self.consul_session:
            self.app.start_consul_shift(self.consul_session.shift.id)

    def _on_next(self) -> None:
        self.app.audio.play("click")
        if self.mode == "traveler" and self.traveler_session:
            self.app.start_traveler_level(self.traveler_session.level.id + 1)
        elif self.mode == "consul" and self.consul_session:
            self.app.start_consul_shift(self.consul_session.shift.id + 1)

    def _on_select(self) -> None:
        self.app.audio.play("click")
        self.app.open_level_select(self.mode)

    def handle_event(self, event: pygame.event.Event) -> None:
        """Process keyboard shortcuts (R to retry, Esc to select) and button clicks."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r:
                self._on_retry()
                return
            if event.key == pygame.K_ESCAPE:
                self._on_select()
                return
        for b in self.buttons:
            b.handle_event(event)

    def update(self, dt: float) -> None:
        """Advance confetti particles and button hover effects."""
        self.particles.update(dt)
        for b in self.buttons:
            b.update(dt)

    def draw(self, surface: pygame.Surface) -> None:
        """Render the results report card and star ratings."""
        surface.fill(COLOR_BG_MAIN)

        box = pygame.Rect(SCREEN_WIDTH // 2 - 410, 60, 820, 595)
        panel = Panel(box, title="OFFICIAL BORDER AUTHORITY REPORT")
        panel.draw(surface, self.app.fonts)

        if self.mode == "traveler" and self.traveler_session:
            self._draw_traveler_report(surface, box, self.traveler_session)
        elif self.mode == "consul" and self.consul_session:
            self._draw_consul_report(surface, box, self.consul_session)

        for b in self.buttons:
            b.draw(surface, self.app.fonts)

        self.particles.draw(surface)

    def _draw_traveler_report(
        self,
        surface: pygame.Surface,
        box: pygame.Rect,
        session: TravelerSession,
    ) -> None:
        f_big = self.app.fonts.get(32, bold=True)
        f_sub = self.app.fonts.get(18, bold=True)
        f_body = self.app.fonts.get(16)

        status_txt = "BORDER CROSSING APPROVED!" if session.won else "BORDER ENTRY DENIED"
        status_col = COLOR_SUCCESS if session.won else COLOR_DANGER
        s_surf = f_big.render(status_txt, True, status_col)
        surface.blit(s_surf, (box.centerx - s_surf.get_width() // 2, box.y + 56))

        # Stars
        for i in range(3):
            draw_star(
                surface,
                (box.centerx - 60 + i * 60, box.y + 128),
                22,
                filled=(i < session.stars_earned),
            )

        # Stats summary
        days_used = session.state.current_day - session.level.start_day
        stats_str = (
            f"Level {session.level.id}: {session.level.title}   •   "
            f"Arrival: Day {session.state.current_day} (Deadline D{session.level.deadline_day})   •   "
            f"Days Used: {days_used}d   •   Budget Left: ${session.state.budget}"
        )
        st_surf = f_sub.render(stats_str, True, COLOR_ACCENT_GOLD)
        surface.blit(st_surf, (box.centerx - st_surf.get_width() // 2, box.y + 175))

        # Validation Reasons Box
        rep_box = pygame.Rect(box.x + 40, box.y + 220, box.width - 80, 275)
        pygame.draw.rect(surface, COLOR_BG_DARK, rep_box, border_radius=8)
        pygame.draw.rect(surface, COLOR_BORDER, rep_box, width=1, border_radius=8)

        hdr = f_sub.render("RULE ENGINE INSPECTION LOG:", True, COLOR_ACCENT_TEAL)
        surface.blit(hdr, (rep_box.x + 18, rep_box.y + 14))

        y = rep_box.y + 48
        if session.won:
            lines = [
                f"✓ All entry requirements for {self.app.db.countries[session.level.destination].name} were satisfied on Day {session.state.current_day}.",
                f"✓ Passport validity buffer and required endorsements verified.",
                f"✓ Remaining travel funds: ${session.state.budget}.",
            ]
            if self.app.progress.is_consul_campaign_unlocked() and session.level.id == 3:
                lines.append("★ BONUS UNLOCKED: You have unlocked the CONSUL CAMPAIGN on the Main Menu!")
            for line in lines:
                y = draw_text_wrapped(
                    surface,
                    line,
                    f_body,
                    COLOR_SUCCESS if "★" not in line else COLOR_ACCENT_GOLD,
                    pygame.Rect(rep_box.x + 18, y, rep_box.width - 36, 55),
                )
                y += 10
        else:
            reasons = (
                session.last_validation.reasons
                if session.last_validation and session.last_validation.reasons
                else ["Unknown validation failure."]
            )
            for r in reasons:
                y = draw_text_wrapped(
                    surface,
                    f"✗ {r}",
                    f_body,
                    COLOR_DANGER,
                    pygame.Rect(rep_box.x + 18, y, rep_box.width - 36, 55),
                )
                y += 8

    def _draw_consul_report(
        self,
        surface: pygame.Surface,
        box: pygame.Rect,
        session: ConsulSession,
    ) -> None:
        f_big = self.app.fonts.get(32, bold=True)
        f_sub = self.app.fonts.get(18, bold=True)
        f_body = self.app.fonts.get(16)

        status_txt = "CONSULAR SHIFT COMPLETED!" if session.won else "SHIFT TERMINATED (TOO MANY STRIKES)"
        status_col = COLOR_SUCCESS if session.won else COLOR_DANGER
        s_surf = f_big.render(status_txt, True, status_col)
        surface.blit(s_surf, (box.centerx - s_surf.get_width() // 2, box.y + 56))

        for i in range(3):
            draw_star(
                surface,
                (box.centerx - 60 + i * 60, box.y + 128),
                22,
                filled=(i < session.stars_earned),
            )

        stats_str = (
            f"{session.shift.title}   •   "
            f"Correct: {session.correct_count}   •   "
            f"Incorrect: {session.incorrect_count}   •   "
            f"Strikes: {session.strikes}/{session.shift.max_strikes}   •   "
            f"Total Earnings: ${session.earnings}"
        )
        st_surf = f_sub.render(stats_str, True, COLOR_ACCENT_GOLD)
        surface.blit(st_surf, (box.centerx - st_surf.get_width() // 2, box.y + 175))

        rep_box = pygame.Rect(box.x + 40, box.y + 220, box.width - 80, 275)
        pygame.draw.rect(surface, COLOR_BG_DARK, rep_box, border_radius=8)
        pygame.draw.rect(surface, COLOR_BORDER, rep_box, width=1, border_radius=8)

        hdr = f_sub.render("MINISTRY AUDIT & PERFORMANCE BREAKDOWN:", True, COLOR_ACCENT_TEAL)
        surface.blit(hdr, (rep_box.x + 18, rep_box.y + 14))

        lines = [
            f"• Total Applicants Processed: {session.current_index} of {len(session.queue)}",
            f"• Correct Verdicts: {session.correct_count} (+${session.shift.pay_per_correct} base per correct verdict)",
            f"• Citations / Strikes Received: {session.strikes} (Max Allowed: {session.shift.max_strikes})",
            f"• Net Consular Salary Earned: ${session.earnings}",
            f"• Rule Most Often Missed: {session.most_missed_rule_description()}",
        ]
        y = rep_box.y + 52
        for line in lines:
            y = draw_text_wrapped(
                surface,
                line,
                f_body,
                COLOR_TEXT_MAIN,
                pygame.Rect(rep_box.x + 18, y, rep_box.width - 36, 45),
            )
            y += 10
