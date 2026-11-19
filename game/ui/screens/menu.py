"""Main Menu screen for BORDER LINES."""

from typing import List, TYPE_CHECKING

import pygame

from game.constants import (
    COLOR_ACCENT_BLUE,
    COLOR_ACCENT_GOLD,
    COLOR_ACCENT_PURPLE,
    COLOR_ACCENT_TEAL,
    COLOR_BG_DARK,
    COLOR_BG_MAIN,
    COLOR_BG_PANEL,
    COLOR_BORDER,
    COLOR_DANGER_DARK,
    COLOR_TEXT_MAIN,
    COLOR_TEXT_MUTED,
    CONSUL_UNLOCK_TRAVELER_LEVELS,
    GAME_SUBTITLE,
    GAME_TITLE,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)
from game.ui.drawing import draw_flag, draw_star
from game.ui.screens import BaseScreen
from game.ui.widgets import Button, Panel, Tooltip

if TYPE_CHECKING:
    from game.app import Game


class MainMenuScreen(BaseScreen):
    """Title screen offering Traveler Campaign, Consul Campaign, How to Play, Settings, and Quit."""

    def __init__(self, app: "Game") -> None:
        super().__init__(app)
        self.buttons: List[Button] = []
        self.tooltip = Tooltip()
        self.anim_time: float = 0.0

    def on_enter(self) -> None:
        """Rebuild menu buttons reflecting current campaign unlock status."""
        self._build_buttons()

    def _build_buttons(self) -> None:
        self.buttons.clear()
        cx = SCREEN_WIDTH // 2
        btn_w = 380
        btn_h = 56
        start_y = 265
        gap = 68

        t_done = self.app.progress.completed_traveler_count()
        t_stars = sum(self.app.progress.traveler_stars.values())
        self.buttons.append(
            Button(
                pygame.Rect(cx - btn_w // 2, start_y, btn_w, btn_h),
                "TRAVELER CAMPAIGN",
                on_click=self._on_traveler,
                bg_color=COLOR_ACCENT_BLUE,
                subtitle=f"Plan Visas & Routes ({t_done}/5 Completed • {t_stars}★)",
                tooltip="Collect passports, visas, and permits under tight deadlines and budgets.",
            )
        )

        consul_unlocked = self.app.progress.is_consul_campaign_unlocked()
        c_stars = sum(self.app.progress.consul_stars.values())
        consul_sub = (
            f"Inspect Applicants at the Desk ({c_stars}/15★)"
            if consul_unlocked
            else f"Locked — Complete {CONSUL_UNLOCK_TRAVELER_LEVELS} Traveler levels to unlock"
        )
        self.buttons.append(
            Button(
                pygame.Rect(cx - btn_w // 2, start_y + gap, btn_w, btn_h),
                "CONSUL CAMPAIGN" if consul_unlocked else "CONSUL CAMPAIGN (LOCKED)",
                on_click=self._on_consul,
                bg_color=COLOR_ACCENT_TEAL,
                subtitle=consul_sub,
                enabled=consul_unlocked,
                tooltip=(
                    "Act as a Consular Officer checking documents against the rulebook."
                    if consul_unlocked
                    else f"Complete the first {CONSUL_UNLOCK_TRAVELER_LEVELS} Traveler Campaign levels to unlock!"
                ),
            )
        )

        self.buttons.append(
            Button(
                pygame.Rect(cx - btn_w // 2, start_y + gap * 2, btn_w, 48),
                "HOW TO PLAY",
                on_click=self._on_howto,
                bg_color=COLOR_ACCENT_PURPLE,
                tooltip="Learn the rules of border control, document prerequisites, and consul inspection.",
            )
        )

        self.buttons.append(
            Button(
                pygame.Rect(cx - btn_w // 2, start_y + gap * 2 + 60, btn_w, 48),
                "SETTINGS",
                on_click=self._on_settings,
                bg_color=COLOR_BG_PANEL,
                tooltip="Adjust audio volume, mute (M), fullscreen (F11), or UI scale.",
            )
        )

        self.buttons.append(
            Button(
                pygame.Rect(cx - btn_w // 2, start_y + gap * 2 + 120, btn_w, 48),
                "QUIT GAME",
                on_click=self._on_quit,
                bg_color=COLOR_DANGER_DARK,
            )
        )

    def _on_traveler(self) -> None:
        self.app.audio.play("click")
        self.app.open_level_select("traveler")

    def _on_consul(self) -> None:
        self.app.audio.play("click")
        self.app.open_level_select("consul")

    def _on_howto(self) -> None:
        self.app.audio.play("click")
        self.app.change_screen("howto")

    def _on_settings(self) -> None:
        self.app.audio.play("click")
        self.app.change_screen("settings")

    def _on_quit(self) -> None:
        self.app.audio.play("click")
        self.app.running = False

    def handle_event(self, event: pygame.event.Event) -> None:
        """Forward events to menu buttons."""
        for b in self.buttons:
            b.handle_event(event)

    def update(self, dt: float) -> None:
        """Update button hover animations."""
        self.anim_time += dt
        for b in self.buttons:
            b.update(dt)

    def draw(self, surface: pygame.Surface) -> None:
        """Render background, flags banner, title header, and menu buttons."""
        surface.fill(COLOR_BG_MAIN)

        # Top decorative passport grid lines
        for x in range(0, SCREEN_WIDTH, 64):
            pygame.draw.line(surface, (34, 43, 58), (x, 0), (x, SCREEN_HEIGHT), 1)
        for y in range(0, SCREEN_HEIGHT, 64):
            pygame.draw.line(surface, (34, 43, 58), (0, y), (SCREEN_WIDTH, y), 1)

        # Header banner
        banner = Panel(pygame.Rect(180, 32, SCREEN_WIDTH - 360, 195), bg_color=COLOR_BG_DARK)
        banner.draw(surface, self.app.fonts)

        f_title = self.app.fonts.get(46, bold=True)
        f_sub = self.app.fonts.get(17, bold=False)

        t_surf = f_title.render(GAME_TITLE, True, COLOR_ACCENT_GOLD)
        surface.blit(t_surf, (SCREEN_WIDTH // 2 - t_surf.get_width() // 2, 52))

        s_surf = f_sub.render(GAME_SUBTITLE, True, COLOR_TEXT_MUTED)
        surface.blit(s_surf, (SCREEN_WIDTH // 2 - s_surf.get_width() // 2, 108))

        # Draw the 6 fictional country flags in a row inside the banner
        countries = list(self.app.db.countries.values())
        total_w = len(countries) * 116
        start_x = SCREEN_WIDTH // 2 - total_w // 2
        f_c = self.app.fonts.get(12, bold=True)
        for idx, cspec in enumerate(countries):
            fx = start_x + idx * 116 + 18
            f_rect = pygame.Rect(fx, 145, 44, 28)
            draw_flag(surface, f_rect, cspec.flag)
            n_surf = f_c.render(cspec.name, True, COLOR_TEXT_MAIN)
            surface.blit(n_surf, (f_rect.centerx - n_surf.get_width() // 2, f_rect.bottom + 5))

        # Draw buttons
        hovered_tip = ""
        for b in self.buttons:
            b.draw(surface, self.app.fonts)
            if b.hovered and b.tooltip:
                hovered_tip = b.tooltip

        # Footer info
        f_foot = self.app.fonts.get(13)
        mute_state = "MUTED" if self.app.progress.settings.muted else "ON"
        foot_txt = (
            f"Shortcuts: [M] Audio: {mute_state}  •  [F11] Fullscreen  •  "
            f"Shared Data-Driven Rules Engine (6 Countries, 7 Document Types)"
        )
        foot_surf = f_foot.render(foot_txt, True, COLOR_TEXT_MUTED)
        surface.blit(foot_surf, (SCREEN_WIDTH // 2 - foot_surf.get_width() // 2, SCREEN_HEIGHT - 32))

        # Decorative stars
        draw_star(surface, (230, 80), 16, True)
        draw_star(surface, (SCREEN_WIDTH - 230, 80), 16, True)

        if hovered_tip:
            self.tooltip.draw(surface, hovered_tip, pygame.mouse.get_pos(), self.app.fonts)
