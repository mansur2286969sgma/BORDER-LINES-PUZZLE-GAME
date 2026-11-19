"""Particle system, easing functions, and stamp animations for BORDER LINES."""

from dataclasses import dataclass
import math
import random
from typing import List, Optional, Tuple

import pygame

from game.constants import COLOR_ACCENT_BLUE, COLOR_ACCENT_GOLD, COLOR_DANGER, COLOR_SUCCESS


def ease_out_cubic(t: float) -> float:
    """Smooth cubic ease-out curve for panel slides and UI transitions."""
    clamped = max(0.0, min(1.0, t))
    return 1.0 - (1.0 - clamped) ** 3


def ease_out_back(t: float) -> float:
    """Overshoot ease-out curve ideal for stamp thumps and badge pop-ins."""
    clamped = max(0.0, min(1.0, t))
    c1 = 1.70158
    c3 = c1 + 1.0
    return 1.0 + c3 * ((clamped - 1.0) ** 3) + c1 * ((clamped - 1.0) ** 2)


@dataclass
class Particle:
    """A single 2D particle for confetti or stamp sparks."""

    x: float
    y: float
    vx: float
    vy: float
    size: float
    color: Tuple[int, int, int]
    life: float
    max_life: float
    gravity: float = 240.0


@dataclass
class StampEffect:
    """Animated rubber stamp impression that thumps onto a document or screen."""

    x: int
    y: int
    label: str
    color: Tuple[int, int, int]
    elapsed: float = 0.0
    duration: float = 0.75


class ParticleSystem:
    """Manages active particles and stamp impression animations."""

    def __init__(self) -> None:
        self.particles: List[Particle] = []
        self.stamps: List[StampEffect] = []
        self._rng = random.Random(777)

    def clear(self) -> None:
        """Remove all active particles and stamp effects."""
        self.particles.clear()
        self.stamps.clear()

    def spawn_confetti(self, x: int, y: int, count: int = 45) -> None:
        """Spawn celebratory confetti burst at (x, y)."""
        palette = [
            COLOR_SUCCESS,
            COLOR_ACCENT_GOLD,
            COLOR_ACCENT_BLUE,
            (237, 137, 54),
            (159, 122, 234),
            (247, 243, 232),
        ]
        for _ in range(count):
            angle = self._rng.uniform(-math.pi * 0.9, -math.pi * 0.1)
            speed = self._rng.uniform(110.0, 340.0)
            life = self._rng.uniform(0.7, 1.45)
            self.particles.append(
                Particle(
                    x=float(x),
                    y=float(y),
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    size=self._rng.uniform(4.0, 8.0),
                    color=self._rng.choice(palette),
                    life=life,
                    max_life=life,
                    gravity=280.0,
                )
            )

    def spawn_stamp_sparks(
        self,
        x: int,
        y: int,
        label: str,
        is_positive: bool = True,
    ) -> None:
        """Trigger a stamp thump animation and radial ink sparks at (x, y)."""
        color = COLOR_SUCCESS if is_positive else COLOR_DANGER
        self.stamps.append(StampEffect(x=x, y=y, label=label, color=color))
        for _ in range(20):
            angle = self._rng.uniform(0.0, math.pi * 2.0)
            speed = self._rng.uniform(50.0, 170.0)
            life = self._rng.uniform(0.25, 0.55)
            self.particles.append(
                Particle(
                    x=float(x),
                    y=float(y),
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    size=self._rng.uniform(2.5, 5.5),
                    color=color,
                    life=life,
                    max_life=life,
                    gravity=80.0,
                )
            )

    def update(self, dt: float) -> None:
        """Advance all active particles and stamp effects by dt seconds."""
        alive: List[Particle] = []
        for p in self.particles:
            p.life -= dt
            if p.life > 0:
                p.x += p.vx * dt
                p.y += p.vy * dt
                p.vy += p.gravity * dt
                alive.append(p)
        self.particles = alive

        active_stamps: List[StampEffect] = []
        for st in self.stamps:
            st.elapsed += dt
            if st.elapsed < st.duration:
                active_stamps.append(st)
        self.stamps = active_stamps

    def draw(self, surface: pygame.Surface, font: Optional[pygame.font.Font] = None) -> None:
        """Render active stamp impressions and particles onto surface."""
        for st in self.stamps:
            progress = min(1.0, st.elapsed / 0.18)
            scale = 1.6 - 0.6 * ease_out_back(progress)
            w = int(170 * scale)
            h = int(54 * scale)
            rect = pygame.Rect(st.x - w // 2, st.y - h // 2, w, h)
            pygame.draw.rect(surface, (248, 245, 236), rect, border_radius=8)
            pygame.draw.rect(surface, st.color, rect, width=4, border_radius=8)
            inner = rect.inflate(-10, -10)
            pygame.draw.rect(surface, st.color, inner, width=1, border_radius=5)
            if font is not None:
                txt = font.render(st.label, True, st.color)
                surface.blit(txt, (rect.centerx - txt.get_width() // 2, rect.centery - txt.get_height() // 2))

        for p in self.particles:
            ratio = max(0.2, p.life / p.max_life)
            sz = max(2, int(p.size * ratio))
            r = pygame.Rect(int(p.x) - sz // 2, int(p.y) - sz // 2, sz, sz)
            pygame.draw.rect(surface, p.color, r, border_radius=2)
