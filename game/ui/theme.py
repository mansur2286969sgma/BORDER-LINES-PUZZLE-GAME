"""Typography, font caching, text wrapping, and UI theme helpers."""

from typing import Dict, List, Tuple

import pygame


class FontBank:
    """Caches system fonts with graceful fallback to Pygame's built-in font."""

    def __init__(self) -> None:
        self._cache: Dict[Tuple[int, bool, bool], pygame.font.Font] = {}
        self.ui_scale: float = 1.0

    def get(self, size: int, bold: bool = False, mono: bool = False) -> pygame.font.Font:
        """Return a cached pygame.font.Font scaled by ui_scale."""
        scaled_size = max(10, int(round(size * self.ui_scale)))
        key = (scaled_size, bold, mono)
        if key not in self._cache:
            if not pygame.font.get_init():
                pygame.font.init()
            font_names = (
                "consolas,couriernew,monospace"
                if mono
                else "segoeui,verdana,arial,dejavusans,sans"
            )
            try:
                f = pygame.font.SysFont(font_names, scaled_size, bold=bold)
            except Exception:
                f = pygame.font.Font(None, scaled_size)
            self._cache[key] = f
        return self._cache[key]

    def set_scale(self, scale: float) -> None:
        """Update UI font scale and clear cached font sizes if changed."""
        clamped = max(0.85, min(1.25, round(scale, 2)))
        if abs(clamped - self.ui_scale) > 0.01:
            self.ui_scale = clamped
            self._cache.clear()


def wrap_text(text: str, font: pygame.font.Font, max_width: int) -> List[str]:
    """Word-wrap a string into lines that fit within max_width pixels."""
    if not text:
        return []
    paragraphs = text.split("\n")
    lines: List[str] = []
    for para in paragraphs:
        words = para.split(" ")
        current = ""
        for w in words:
            test = f"{current} {w}".strip() if current else w
            if font.size(test)[0] <= max_width or not current:
                current = test
            else:
                lines.append(current)
                current = w
        if current:
            lines.append(current)
    return lines


def draw_text_wrapped(
    surface: pygame.Surface,
    text: str,
    font: pygame.font.Font,
    color: Tuple[int, int, int],
    rect: pygame.Rect,
    line_spacing: int = 4,
    align: str = "left",
) -> int:
    """Render word-wrapped text inside rect and return the bottom Y coordinate."""
    lines = wrap_text(text, font, rect.width)
    y = rect.top
    for line in lines:
        if y + font.get_linesize() > rect.bottom + 4:
            break
        surf = font.render(line, True, color)
        if align == "center":
            x = rect.centerx - surf.get_width() // 2
        elif align == "right":
            x = rect.right - surf.get_width()
        else:
            x = rect.left
        surface.blit(surf, (x, y))
        y += font.get_linesize() + line_spacing
    return y
