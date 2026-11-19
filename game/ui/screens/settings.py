"""Settings screen for audio volume sliders, mute toggle, fullscreen, UI scale, and progress reset."""

from typing import List, TYPE_CHECKING

import pygame

from game.constants import (
    COLOR_ACCENT_BLUE,
    COLOR_ACCENT_GOLD,
    COLOR_ACCENT_TEAL,
    COLOR_BG_MAIN,
    COLOR_BG_PANEL,
    COLOR_BG_PANEL_ALT,
    COLOR_DANGER_DARK,
    COLOR_TEXT_MUTED,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)
from game.ui.screens import BaseScreen
from game.ui.widgets import Button, Panel, Slider

if TYPE_CHECKING:
    from game.app import Game


class SettingsScreen(BaseScreen):
    """Settings screen allowing real-time adjustment of audio, display, UI scale, and save data."""

    def __init__(self, app: "Game") -> None:
        super().__init__(app)
        self.back_button = Button(
            pygame.Rect(40, 26, 150, 42),
            "← Main Menu",
            on_click=self._on_back,
            bg_color=COLOR_BG_PANEL,
        )
        self.sliders: List[Slider] = []
        self.buttons: List[Button] = []
        self.status_message: str = ""

    def on_enter(self) -> None:
        """Build sliders and toggle buttons reflecting current settings."""
        self.status_message = ""
        self._build_controls()

    def _build_controls(self) -> None:
        s = self.app.progress.settings
        cx = SCREEN_WIDTH // 2
        w = 420

        self.sliders = [
            Slider(
                pygame.Rect(cx - w // 2, 165, w, 46),
                "Sound Effects Volume",
                value=s.sfx_volume,
                min_val=0.0,
                max_val=1.0,
                on_change=self._on_sfx_change,
            ),
            Slider(
                pygame.Rect(cx - w // 2, 235, w, 46),
                "Ambient Music Volume",
                value=s.music_volume,
                min_val=0.0,
                max_val=1.0,
                on_change=self._on_music_change,
            ),
            Slider(
                pygame.Rect(cx - w // 2, 305, w, 46),
                "Typography / UI Scale",
                value=s.ui_scale,
                min_val=0.85,
                max_val=1.20,
                on_change=self._on_scale_change,
            ),
        ]

        mute_label = "AUDIO: MUTED (Press M to Unmute)" if s.muted else "AUDIO: ACTIVE (Press M to Mute)"
        fs_label = "DISPLAY: FULLSCREEN [F11]" if s.fullscreen else "DISPLAY: WINDOWED [F11]"

        self.buttons = [
            Button(
                pygame.Rect(cx - w // 2, 380, w, 46),
                mute_label,
                on_click=self._on_toggle_mute,
                bg_color=COLOR_ACCENT_TEAL if not s.muted else COLOR_BG_PANEL_ALT,
            ),
            Button(
                pygame.Rect(cx - w // 2, 438, w, 46),
                fs_label,
                on_click=self._on_toggle_fullscreen,
                bg_color=COLOR_ACCENT_BLUE,
            ),
            Button(
                pygame.Rect(cx - w // 2, 496, 202, 46),
                "Unlock All Campaigns",
                on_click=self._on_unlock_all,
                bg_color=COLOR_BG_PANEL_ALT,
            ),
            Button(
                pygame.Rect(cx + 8, 496, 202, 46),
                "Reset Progress",
                on_click=self._on_reset_progress,
                bg_color=COLOR_DANGER_DARK,
            ),
        ]

    def _on_sfx_change(self, val: float) -> None:
        self.app.progress.settings.sfx_volume = val
        self.app.audio.apply_volume()

    def _on_music_change(self, val: float) -> None:
        self.app.progress.settings.music_volume = val
        self.app.audio.apply_volume()

    def _on_scale_change(self, val: float) -> None:
        self.app.progress.settings.ui_scale = val
        self.app.fonts.set_scale(val)

    def _on_toggle_mute(self) -> None:
        self.app.audio.toggle_mute()
        self.app.audio.play("click")
        self.app.progress.save()
        self._build_controls()

    def _on_toggle_fullscreen(self) -> None:
        self.app.audio.play("click")
        self.app.toggle_fullscreen()
        self._build_controls()

    def _on_unlock_all(self) -> None:
        self.app.audio.play("coin")
        self.app.progress.unlock_all()
        self.status_message = "All Traveler levels and Consul shifts unlocked!"

    def _on_reset_progress(self) -> None:
        self.app.audio.play("error")
        self.app.progress.reset_progress()
        self.status_message = "Progress reset to default (Consul campaign locked)."

    def _on_back(self) -> None:
        self.app.audio.play("click")
        self.app.progress.save()
        self.app.change_screen("menu")

    def handle_event(self, event: pygame.event.Event) -> None:
        """Forward events to sliders and buttons."""
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._on_back()
            return
        self.back_button.handle_event(event)
        for sl in self.sliders:
            if sl.handle_event(event) and event.type == pygame.MOUSEBUTTONUP:
                self.app.audio.play("click")
                self.app.progress.save()
        for b in self.buttons:
            b.handle_event(event)

    def update(self, dt: float) -> None:
        """Update button hover animations."""
        self.back_button.update(dt)
        for b in self.buttons:
            b.update(dt)

    def draw(self, surface: pygame.Surface) -> None:
        """Render settings panel, sliders, and action buttons."""
        surface.fill(COLOR_BG_MAIN)
        self.back_button.draw(surface, self.app.fonts)

        box = pygame.Rect(SCREEN_WIDTH // 2 - 280, 95, 560, 520)
        panel = Panel(box, title="SYSTEM & BUREAU SETTINGS")
        panel.draw(surface, self.app.fonts)

        for sl in self.sliders:
            sl.draw(surface, self.app.fonts)
        for b in self.buttons:
            b.draw(surface, self.app.fonts)

        f_info = self.app.fonts.get(14, bold=True)
        if self.status_message:
            s_surf = f_info.render(self.status_message, True, COLOR_ACCENT_GOLD)
            surface.blit(s_surf, (box.centerx - s_surf.get_width() // 2, box.bottom - 52))

        f_path = self.app.fonts.get(12)
        p_surf = f_path.render(f"Save File: {self.app.progress.save_path}", True, COLOR_TEXT_MUTED)
        surface.blit(p_surf, (box.centerx - p_surf.get_width() // 2, box.bottom - 26))
