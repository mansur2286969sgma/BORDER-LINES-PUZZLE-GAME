"""Main Game controller, Pygame window setup, and screen state machine for BORDER LINES."""

import os
from typing import Dict, Optional

import pygame

from game.campaigns.consul import ConsulSession
from game.campaigns.traveler import TravelerSession
from game.constants import FPS, GAME_TITLE, SCREEN_HEIGHT, SCREEN_WIDTH
from game.core.loader import GameDatabase, load_game_database
from game.core.rules import RuleEngine
from game.systems.audio import AudioManager
from game.systems.progress import ProgressManager
from game.ui.screens import BaseScreen
from game.ui.screens.consul_screen import ConsulScreen
from game.ui.screens.howto import HowToPlayScreen
from game.ui.screens.level_select import LevelSelectScreen
from game.ui.screens.menu import MainMenuScreen
from game.ui.screens.results import ResultsScreen
from game.ui.screens.settings import SettingsScreen
from game.ui.screens.traveler_screen import TravelerScreen
from game.ui.theme import FontBank


class Game:
    """Top-level application class owning the main loop, state machine, database, and systems."""

    def __init__(
        self,
        project_root: str,
        unlock_all: bool = False,
        reset_progress: bool = False,
    ) -> None:
        """Initialize Pygame, load JSON database, set up audio/progress, and create screens."""
        self.project_root: str = project_root
        self.data_dir: str = os.path.join(project_root, "data")

        # Load data and initialize pure-Python rules engine first
        self.db: GameDatabase = load_game_database(self.data_dir)
        self.engine: RuleEngine = RuleEngine(self.db.countries, self.db.documents)

        # Load user progress & settings
        self.progress: ProgressManager = ProgressManager(project_root)
        if reset_progress:
            self.progress.reset_progress()
        if unlock_all:
            self.progress.unlock_all()

        # Initialize Pygame display & font bank
        pygame.init()
        pygame.display.set_caption(GAME_TITLE)
        self.screen: pygame.Surface = self._create_display_surface(
            self.progress.settings.fullscreen
        )
        self.clock: pygame.time.Clock = pygame.time.Clock()
        self.fonts: FontBank = FontBank()
        self.fonts.set_scale(self.progress.settings.ui_scale)

        # Initialize procedural audio
        self.audio: AudioManager = AudioManager(self.progress.settings)
        self.audio.start_music()

        # Register screens in the state machine
        self.screens: Dict[str, BaseScreen] = {
            "menu": MainMenuScreen(self),
            "level_select": LevelSelectScreen(self),
            "traveler": TravelerScreen(self),
            "consul": ConsulScreen(self),
            "results": ResultsScreen(self),
            "howto": HowToPlayScreen(self),
            "settings": SettingsScreen(self),
        }
        self.current_screen_name: str = "menu"
        self.current_screen: BaseScreen = self.screens["menu"]
        self.current_screen.on_enter()
        self.running: bool = True

    def _create_display_surface(self, fullscreen: bool) -> pygame.Surface:
        """Create a 1280x720 window using pygame.SCALED | pygame.RESIZABLE with safe fallbacks."""
        flags = pygame.SCALED | pygame.RESIZABLE
        if fullscreen:
            flags |= pygame.FULLSCREEN
        try:
            return pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), flags)
        except pygame.error:
            # Fallback for dummy video drivers or environments that do not support SCALED
            return pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))

    def toggle_fullscreen(self) -> None:
        """Toggle fullscreen display mode safely."""
        self.progress.settings.fullscreen = not self.progress.settings.fullscreen
        self.screen = self._create_display_surface(self.progress.settings.fullscreen)
        self.progress.save()

    def change_screen(self, name: str) -> None:
        """Transition from the current screen to the named screen."""
        if name not in self.screens:
            raise ValueError(f"Unknown screen '{name}'")
        self.current_screen.on_exit()
        self.current_screen_name = name
        self.current_screen = self.screens[name]
        self.current_screen.on_enter()

    def open_level_select(self, campaign_mode: str) -> None:
        """Open the level/shift selector for 'traveler' or 'consul'."""
        ls = self.screens["level_select"]
        if isinstance(ls, LevelSelectScreen):
            ls.set_campaign(campaign_mode)
        self.change_screen("level_select")

    def start_traveler_level(self, level_id: int) -> None:
        """Load and transition into Traveler level_id."""
        lvl = next((l for l in self.db.traveler_levels if l.id == level_id), None)
        if lvl is None:
            return
        ts = self.screens["traveler"]
        if isinstance(ts, TravelerScreen):
            ts.load_level(lvl)
        self.change_screen("traveler")

    def start_consul_shift(self, shift_id: int) -> None:
        """Load and transition into Consul shift_id."""
        sh = next((s for s in self.db.consul_shifts if s.id == shift_id), None)
        if sh is None:
            return
        cs = self.screens["consul"]
        if isinstance(cs, ConsulScreen):
            cs.load_shift(sh)
        self.change_screen("consul")

    def show_traveler_results(self, session: TravelerSession) -> None:
        """Transition to the Results screen for a completed Traveler level attempt."""
        rs = self.screens["results"]
        if isinstance(rs, ResultsScreen):
            rs.set_traveler_result(session)
        self.change_screen("results")

    def show_consul_results(self, session: ConsulSession) -> None:
        """Transition to the Results screen for a completed Consul shift."""
        rs = self.screens["results"]
        if isinstance(rs, ResultsScreen):
            rs.set_consul_result(session)
        self.change_screen("results")

    def step_frame(self, dt: Optional[float] = None) -> None:
        """Process events, update active screen, and render a single frame."""
        frame_dt = dt if dt is not None else min(0.1, self.clock.tick(FPS) / 1000.0)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_m:
                    self.audio.toggle_mute()
                    self.progress.save()
                    if self.current_screen_name == "settings":
                        self.current_screen.on_enter()
                    continue
                if event.key == pygame.K_F11:
                    self.toggle_fullscreen()
                    if self.current_screen_name == "settings":
                        self.current_screen.on_enter()
                    continue
            self.current_screen.handle_event(event)

        self.current_screen.update(frame_dt)
        self.current_screen.draw(self.screen)
        pygame.display.flip()

    def run(self) -> None:
        """Run the main 60 FPS game loop until quit."""
        while self.running:
            self.step_frame()
        self.progress.save()
        pygame.quit()
