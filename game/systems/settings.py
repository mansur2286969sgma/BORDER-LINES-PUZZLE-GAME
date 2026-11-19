"""Settings model for sound volume, mute, fullscreen, and UI scaling."""

from dataclasses import dataclass
from typing import Any, Dict

from game.constants import DEFAULT_MUSIC_VOLUME, DEFAULT_SFX_VOLUME


@dataclass
class GameSettings:
    """User-configurable game settings persisted inside the save file."""

    sfx_volume: float = DEFAULT_SFX_VOLUME
    music_volume: float = DEFAULT_MUSIC_VOLUME
    muted: bool = False
    fullscreen: bool = False
    ui_scale: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize settings to a JSON-friendly dictionary."""
        return {
            "sfx_volume": round(float(self.sfx_volume), 2),
            "music_volume": round(float(self.music_volume), 2),
            "muted": bool(self.muted),
            "fullscreen": bool(self.fullscreen),
            "ui_scale": round(float(self.ui_scale), 2),
        }

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "GameSettings":
        """Deserialize settings safely from a dictionary with clamping and fallbacks."""
        if not isinstance(raw, dict):
            return cls()
        try:
            sfx = max(0.0, min(1.0, float(raw.get("sfx_volume", DEFAULT_SFX_VOLUME))))
            music = max(0.0, min(1.0, float(raw.get("music_volume", DEFAULT_MUSIC_VOLUME))))
            muted = bool(raw.get("muted", False))
            fullscreen = bool(raw.get("fullscreen", False))
            ui_scale = max(0.85, min(1.25, float(raw.get("ui_scale", 1.0))))
            return cls(
                sfx_volume=sfx,
                music_volume=music,
                muted=muted,
                fullscreen=fullscreen,
                ui_scale=ui_scale,
            )
        except (ValueError, TypeError):
            return cls()
