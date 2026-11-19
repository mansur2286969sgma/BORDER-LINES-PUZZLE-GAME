"""Level and Shift Selection screen for both Traveler and Consul campaigns."""

from typing import List, TYPE_CHECKING

import pygame

from game.constants import (
    COLOR_ACCENT_BLUE,
    COLOR_ACCENT_GOLD,
    COLOR_ACCENT_TEAL,
    COLOR_BG_DARK,
    COLOR_BG_MAIN,
    COLOR_BG_PANEL,
    COLOR_BORDER,
    COLOR_SUCCESS_DARK,
    COLOR_TEXT_MAIN,
    COLOR_TEXT_MUTED,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)
from game.ui.drawing import draw_flag, draw_star
from game.ui.screens import BaseScreen
from game.ui.theme import draw_text_wrapped
from game.ui.widgets import Button, Panel

if TYPE_CHECKING:
    from game.app import Game


class LevelSelectScreen(BaseScreen):
    """Displays the 5 Traveler levels or 5 Consul shifts with star ratings and unlock status."""

    def __init__(self, app: "Game") -> None:
        super().__init__(app)
        self.campaign_mode: str = "traveler"
        self.play_buttons: List[Button] = []
        self.back_button: Button = Button(
            pygame.Rect(40, 28, 150, 42),
            "← Main Menu",
            on_click=self._on_back,
            bg_color=COLOR_BG_PANEL,
        )

    def set_campaign(self, mode: str) -> None:
        """Select 'traveler' or 'consul' mode before entering."""
        self.campaign_mode = mode

    def on_enter(self) -> None:
        """Rebuild level/shift cards and action buttons."""
        self._build_buttons()

    def _build_buttons(self) -> None:
        self.play_buttons.clear()
        items = (
            self.app.db.traveler_levels
            if self.campaign_mode == "traveler"
            else self.app.db.consul_shifts
        )
        start_y = 105
        row_h = 112

        for idx, item in enumerate(items):
            y = start_y + idx * row_h
            if self.campaign_mode == "traveler":
                unlocked = self.app.progress.is_traveler_level_unlocked(item.id)
                stars = self.app.progress.traveler_stars.get(item.id, 0)
            else:
                unlocked = self.app.progress.is_consul_shift_unlocked(item.id)
                stars = self.app.progress.consul_stars.get(item.id, 0)

            btn_label = "PLAY" if stars == 0 else "REPLAY"
            if not unlocked:
                btn_label = "LOCKED"

            btn_color = (
                COLOR_SUCCESS_DARK
                if stars > 0
                else (COLOR_ACCENT_BLUE if self.campaign_mode == "traveler" else COLOR_ACCENT_TEAL)
            )
            level_id = item.id
            self.play_buttons.append(
                Button(
                    pygame.Rect(SCREEN_WIDTH - 230, y + 26, 150, 48),
                    btn_label,
                    on_click=lambda lid=level_id: self._on_start_item(lid),
                    bg_color=btn_color,
                    enabled=unlocked,
                )
            )

    def _on_back(self) -> None:
        self.app.audio.play("click")
        self.app.change_screen("menu")

    def _on_start_item(self, item_id: int) -> None:
        self.app.audio.play("click")
        if self.campaign_mode == "traveler":
            self.app.start_traveler_level(item_id)
        else:
            self.app.start_consul_shift(item_id)

    def handle_event(self, event: pygame.event.Event) -> None:
        """Handle mouse clicks and Esc key."""
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._on_back()
            return
        self.back_button.handle_event(event)
        for b in self.play_buttons:
            b.handle_event(event)

    def update(self, dt: float) -> None:
        """Update button animations."""
        self.back_button.update(dt)
        for b in self.play_buttons:
            b.update(dt)

    def draw(self, surface: pygame.Surface) -> None:
        """Render the campaign title and 5 level/shift cards."""
        surface.fill(COLOR_BG_MAIN)
        self.back_button.draw(surface, self.app.fonts)

        f_hdr = self.app.fonts.get(30, bold=True)
        f_title = self.app.fonts.get(20, bold=True)
        f_sub = self.app.fonts.get(14, bold=True)
        f_body = self.app.fonts.get(14, bold=False)

        header_text = (
            "TRAVELER CAMPAIGN — SELECT JOURNEY"
            if self.campaign_mode == "traveler"
            else "CONSUL CAMPAIGN — SELECT BORDER SHIFT"
        )
        hdr_surf = f_hdr.render(header_text, True, COLOR_ACCENT_GOLD)
        surface.blit(hdr_surf, (SCREEN_WIDTH // 2 - hdr_surf.get_width() // 2, 32))

        items = (
            self.app.db.traveler_levels
            if self.campaign_mode == "traveler"
            else self.app.db.consul_shifts
        )
        start_y = 105
        row_h = 112

        for idx, item in enumerate(items):
            y = start_y + idx * row_h
            card_rect = pygame.Rect(40, y, SCREEN_WIDTH - 80, 98)
            if self.campaign_mode == "traveler":
                unlocked = self.app.progress.is_traveler_level_unlocked(item.id)
                stars = self.app.progress.traveler_stars.get(item.id, 0)
                dest_country = self.app.db.countries[item.destination]
                meta_text = (
                    f"Route: {self.app.db.countries[item.origin].name} → {dest_country.name}   |   "
                    f"Budget: ${item.start_budget}   |   Deadline: Day {item.deadline_day}"
                )
                desc_text = item.goal_text
            else:
                unlocked = self.app.progress.is_consul_shift_unlocked(item.id)
                stars = self.app.progress.consul_stars.get(item.id, 0)
                best = self.app.progress.consul_best_scores.get(item.id, 0)
                dest_country = self.app.db.countries[item.destination]
                timer_str = f"{item.time_limit_seconds}s Timer" if item.time_limit_seconds > 0 else "No Timer"
                meta_text = (
                    f"Post: {dest_country.name}   |   Applicants: {item.applicant_count}   |   "
                    f"{timer_str}   |   Best Pay: ${best}"
                )
                desc_text = item.subtitle

            panel = Panel(
                card_rect,
                bg_color=COLOR_BG_PANEL if unlocked else COLOR_BG_DARK,
                border_color=COLOR_ACCENT_GOLD if stars == 3 else COLOR_BORDER,
            )
            panel.draw(surface, self.app.fonts)

            # Destination flag
            flag_rect = pygame.Rect(card_rect.x + 18, card_rect.y + 18, 54, 36)
            draw_flag(surface, flag_rect, dest_country.flag)

            # Stars below flag
            for s_idx in range(3):
                draw_star(
                    surface,
                    (flag_rect.x + 9 + s_idx * 18, flag_rect.bottom + 18),
                    7,
                    filled=(s_idx < stars),
                )

            # Title & description
            title_str = (
                f"Level {item.id}: {item.title} — {item.subtitle}"
                if self.campaign_mode == "traveler"
                else item.title
            )
            t_col = COLOR_TEXT_MAIN if unlocked else COLOR_TEXT_MUTED
            t_surf = f_title.render(title_str, True, t_col)
            surface.blit(t_surf, (card_rect.x + 92, card_rect.y + 14))

            m_surf = f_sub.render(meta_text, True, COLOR_ACCENT_GOLD if unlocked else COLOR_TEXT_MUTED)
            surface.blit(m_surf, (card_rect.x + 92, card_rect.y + 42))

            draw_text_wrapped(
                surface,
                desc_text,
                f_body,
                COLOR_TEXT_MUTED,
                pygame.Rect(card_rect.x + 92, card_rect.y + 66, card_rect.width - 320, 26),
            )

            self.play_buttons[idx].draw(surface, self.app.fonts)
