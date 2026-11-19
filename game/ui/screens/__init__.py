"""Base screen interface and screen package initialization for BORDER LINES."""

from typing import TYPE_CHECKING

import pygame

if TYPE_CHECKING:
    from game.app import Game


class BaseScreen:
    """Common base class for all game screens managed by the state machine."""

    def __init__(self, app: "Game") -> None:
        """Store a reference to the main Game controller."""
        self.app: "Game" = app

    def on_enter(self) -> None:
        """Called when this screen becomes the active screen."""

    def handle_event(self, event: pygame.event.Event) -> None:
        """Handle a single Pygame input event."""

    def update(self, dt: float) -> None:
        """Advance animations, timers, and logic by dt seconds."""

    def draw(self, surface: pygame.Surface) -> None:
        """Render the screen onto surface."""

    def on_exit(self) -> None:
        """Called when transitioning away from this screen."""
