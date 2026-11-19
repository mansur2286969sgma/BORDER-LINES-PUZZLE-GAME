"""Save/load progress manager with safe user directory fallback and unlock logic."""

import json
import os
from typing import Any, Dict, Optional

from game.constants import CONSUL_UNLOCK_TRAVELER_LEVELS
from game.systems.settings import GameSettings


class ProgressManager:
    """Manages player progression, stars, best scores, campaign unlock state, and settings IO."""

    def __init__(self, project_root: str, custom_save_path: Optional[str] = None) -> None:
        """Initialize progress manager and load existing progress if available."""
        self.project_root = project_root
        self.save_path = custom_save_path or self._resolve_save_path()
        self.traveler_stars: Dict[int, int] = {}
        self.consul_stars: Dict[int, int] = {}
        self.consul_best_scores: Dict[int, int] = {}
        self.unlock_all_override: bool = False
        self.settings: GameSettings = GameSettings()
        self.load()

    def _resolve_save_path(self) -> str:
        """Choose a writable user save path via os.path.expanduser with fallback to project root."""
        try:
            home = os.path.expanduser("~")
            if home and home != "~" and os.path.isdir(home):
                save_dir = os.path.join(home, ".border_lines")
                os.makedirs(save_dir, exist_ok=True)
                return os.path.join(save_dir, "progress.json")
        except OSError:
            pass
        return os.path.join(self.project_root, "progress.json")

    def load(self) -> None:
        """Load progress and settings from JSON, ignoring corrupted files gracefully."""
        if not os.path.isfile(self.save_path):
            return
        try:
            with open(self.save_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                return
            t_stars = data.get("traveler_stars", {})
            if isinstance(t_stars, dict):
                self.traveler_stars = {int(k): int(v) for k, v in t_stars.items()}
            c_stars = data.get("consul_stars", {})
            if isinstance(c_stars, dict):
                self.consul_stars = {int(k): int(v) for k, v in c_stars.items()}
            c_scores = data.get("consul_best_scores", {})
            if isinstance(c_scores, dict):
                self.consul_best_scores = {int(k): int(v) for k, v in c_scores.items()}
            self.unlock_all_override = bool(data.get("unlock_all_override", False))
            self.settings = GameSettings.from_dict(data.get("settings", {}))
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            # Corrupted file never crashes the game
            self.traveler_stars = {}
            self.consul_stars = {}
            self.consul_best_scores = {}
            self.settings = GameSettings()

    def save(self) -> None:
        """Persist current progress and settings to disk, falling back to project folder on error."""
        payload: Dict[str, Any] = {
            "traveler_stars": {str(k): v for k, v in self.traveler_stars.items()},
            "consul_stars": {str(k): v for k, v in self.consul_stars.items()},
            "consul_best_scores": {str(k): v for k, v in self.consul_best_scores.items()},
            "unlock_all_override": self.unlock_all_override,
            "settings": self.settings.to_dict(),
        }
        try:
            with open(self.save_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
        except OSError:
            fallback = os.path.join(self.project_root, "progress.json")
            try:
                with open(fallback, "w", encoding="utf-8") as f:
                    json.dump(payload, f, indent=2)
                self.save_path = fallback
            except OSError:
                pass

    def reset_progress(self) -> None:
        """Clear all completed levels, stars, and overrides, then save."""
        self.traveler_stars.clear()
        self.consul_stars.clear()
        self.consul_best_scores.clear()
        self.unlock_all_override = False
        self.save()

    def unlock_all(self) -> None:
        """Unlock all Traveler levels and Consul shifts immediately."""
        self.unlock_all_override = True
        for lvl in range(1, 6):
            self.traveler_stars.setdefault(lvl, 1)
        for sh in range(1, 6):
            self.consul_stars.setdefault(sh, 1)
        self.save()

    def completed_traveler_count(self) -> int:
        """Return how many Traveler levels have been completed with at least 1 star."""
        return sum(1 for stars in self.traveler_stars.values() if stars > 0)

    def is_consul_campaign_unlocked(self) -> bool:
        """Return True if the Consul campaign is unlocked (3+ Traveler levels completed or --unlock-all)."""
        if self.unlock_all_override:
            return True
        completed_first_three = all(self.traveler_stars.get(i, 0) > 0 for i in range(1, CONSUL_UNLOCK_TRAVELER_LEVELS + 1))
        return completed_first_three or self.completed_traveler_count() >= CONSUL_UNLOCK_TRAVELER_LEVELS

    def is_traveler_level_unlocked(self, level_id: int) -> bool:
        """Return True if Traveler level_id is unlocked."""
        if self.unlock_all_override or level_id <= 1:
            return True
        return self.traveler_stars.get(level_id - 1, 0) > 0

    def is_consul_shift_unlocked(self, shift_id: int) -> bool:
        """Return True if Consul shift_id is unlocked."""
        if not self.is_consul_campaign_unlocked():
            return False
        if self.unlock_all_override or shift_id <= 1:
            return True
        return self.consul_stars.get(shift_id - 1, 0) > 0

    def record_traveler_completion(self, level_id: int, stars: int) -> None:
        """Record stars earned on a Traveler level and save progress."""
        prev = self.traveler_stars.get(level_id, 0)
        if stars > prev:
            self.traveler_stars[level_id] = stars
        self.save()

    def record_consul_completion(self, shift_id: int, stars: int, earnings: int) -> None:
        """Record stars and earnings on a Consul shift and save progress."""
        prev_stars = self.consul_stars.get(shift_id, 0)
        if stars > prev_stars:
            self.consul_stars[shift_id] = stars
        prev_score = self.consul_best_scores.get(shift_id, 0)
        if earnings > prev_score:
            self.consul_best_scores[shift_id] = earnings
        self.save()
