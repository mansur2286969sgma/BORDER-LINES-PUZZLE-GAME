"""Procedural drawing utilities for flags, portraits, stamps, stars, and world maps."""

import math
from typing import Dict, List, Optional, Tuple

import pygame

from game.constants import (
    COLOR_ACCENT_BLUE,
    COLOR_ACCENT_GOLD,
    COLOR_ACCENT_ORANGE,
    COLOR_BG_DARK,
    COLOR_BORDER,
    COLOR_DANGER,
    COLOR_SHADOW,
    COLOR_SUCCESS,
    COLOR_TEXT_MAIN,
    COLOR_TEXT_MUTED,
)
from game.core.models import CountrySpec, FlagSpec, PortraitSpec


def draw_flag(surface: pygame.Surface, rect: pygame.Rect, flag: FlagSpec) -> None:
    """Draw a procedural country flag inside rect from simple shapes and colors."""
    colors = flag.colors
    c0 = colors[0] if len(colors) > 0 else (60, 80, 120)
    c1 = colors[1] if len(colors) > 1 else (230, 235, 240)
    c2 = colors[2] if len(colors) > 2 else c0

    pygame.draw.rect(surface, c0, rect, border_radius=4)

    if flag.style == "tricolor_h":
        h3 = rect.height // 3
        pygame.draw.rect(surface, c0, (rect.x, rect.y, rect.width, h3))
        pygame.draw.rect(surface, c1, (rect.x, rect.y + h3, rect.width, h3))
        pygame.draw.rect(surface, c2, (rect.x, rect.y + 2 * h3, rect.width, rect.height - 2 * h3))
    elif flag.style == "tricolor_v":
        w3 = rect.width // 3
        pygame.draw.rect(surface, c0, (rect.x, rect.y, w3, rect.height))
        pygame.draw.rect(surface, c1, (rect.x + w3, rect.y, w3, rect.height))
        pygame.draw.rect(surface, c2, (rect.x + 2 * w3, rect.y, rect.width - 2 * w3, rect.height))
    elif flag.style == "bicolor_h":
        h2 = rect.height // 2
        pygame.draw.rect(surface, c0, (rect.x, rect.y, rect.width, h2))
        pygame.draw.rect(surface, c1, (rect.x, rect.y + h2, rect.width, rect.height - h2))
    elif flag.style == "nordic_cross":
        pygame.draw.rect(surface, c0, rect)
        cx = rect.x + int(rect.width * 0.35)
        cy = rect.centery
        bar = max(4, rect.height // 5)
        pygame.draw.rect(surface, c1, (cx - bar // 2, rect.y, bar, rect.height))
        pygame.draw.rect(surface, c1, (rect.x, cy - bar // 2, rect.width, bar))
        inner = max(2, bar // 2)
        pygame.draw.rect(surface, c2, (cx - inner // 2, rect.y, inner, rect.height))
        pygame.draw.rect(surface, c2, (rect.x, cy - inner // 2, rect.width, inner))
    elif flag.style == "diagonal":
        pygame.draw.rect(surface, c0, rect)
        pts = [
            (rect.left, rect.bottom),
            (rect.right, rect.top),
            (rect.right, rect.bottom),
        ]
        pygame.draw.polygon(surface, c2, pts)
        pygame.draw.line(surface, c1, (rect.left, rect.bottom), (rect.right, rect.top), max(3, rect.height // 7))
    elif flag.style == "stripes":
        stripes = 5
        sh = max(2, rect.height // stripes)
        for i in range(stripes):
            col = c0 if i % 2 == 0 else c1
            y_pos = rect.y + i * sh
            h_cur = rect.bottom - y_pos if i == stripes - 1 else sh
            pygame.draw.rect(surface, col, (rect.x, y_pos, rect.width, h_cur))
        pygame.draw.polygon(
            surface,
            c2,
            [(rect.left, rect.top), (rect.left + rect.width // 2, rect.centery), (rect.left, rect.bottom)],
        )

    # Draw emblem if present
    cx, cy = rect.centerx, rect.centery
    r = max(4, min(rect.width, rect.height) // 5)
    if flag.emblem == "circle" or flag.emblem == "sun":
        pygame.draw.circle(surface, flag.emblem_color, (cx, cy), r)
        if flag.emblem == "sun":
            for a in range(0, 360, 45):
                rad = math.radians(a)
                x2 = cx + int(math.cos(rad) * (r + 4))
                y2 = cy + int(math.sin(rad) * (r + 4))
                pygame.draw.line(surface, flag.emblem_color, (cx, cy), (x2, y2), 2)
    elif flag.emblem == "diamond":
        pts = [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)]
        pygame.draw.polygon(surface, flag.emblem_color, pts)
    elif flag.emblem == "star":
        pts = []
        for i in range(10):
            angle = math.radians(i * 36 - 90)
            rad_len = r if i % 2 == 0 else max(2, r // 2)
            pts.append((cx + int(math.cos(angle) * rad_len), cy + int(math.sin(angle) * rad_len)))
        pygame.draw.polygon(surface, flag.emblem_color, pts)

    pygame.draw.rect(surface, (25, 32, 44), rect, width=1, border_radius=4)


def draw_portrait(surface: pygame.Surface, rect: pygame.Rect, spec: PortraitSpec) -> None:
    """Draw a stylized procedural applicant portrait inside rect."""
    pygame.draw.rect(surface, (215, 224, 232), rect, border_radius=6)

    cx = rect.centerx
    # Shoulders / shirt
    shirt_h = int(rect.height * 0.34)
    shirt_rect = pygame.Rect(
        rect.x + int(rect.width * 0.14),
        rect.bottom - shirt_h,
        int(rect.width * 0.72),
        shirt_h,
    )
    pygame.draw.rect(surface, spec.shirt_color, shirt_rect, border_top_left_radius=18, border_top_right_radius=18)

    # Collar accent
    pygame.draw.polygon(
        surface,
        (240, 244, 248),
        [
            (cx - 10, shirt_rect.top),
            (cx + 10, shirt_rect.top),
            (cx, shirt_rect.top + 14),
        ],
    )

    # Neck
    neck_w = max(10, int(rect.width * 0.18))
    neck_h = max(10, int(rect.height * 0.14))
    pygame.draw.rect(
        surface,
        spec.skin_color,
        (cx - neck_w // 2, shirt_rect.top - neck_h + 4, neck_w, neck_h),
    )

    # Head
    head_r = int(min(rect.width, rect.height) * 0.24)
    head_cy = rect.y + int(rect.height * 0.42)
    pygame.draw.circle(surface, spec.skin_color, (cx, head_cy), head_r)

    # Hair styles
    if spec.hair_style == 0:
        pygame.draw.arc(
            surface,
            spec.hair_color,
            (cx - head_r - 2, head_cy - head_r - 4, (head_r + 2) * 2, head_r * 2),
            0.15,
            math.pi - 0.15,
            max(6, head_r // 2),
        )
    elif spec.hair_style == 1:
        pygame.draw.rect(
            surface,
            spec.hair_color,
            (cx - head_r, head_cy - head_r - 4, head_r * 2, int(head_r * 0.65)),
            border_top_left_radius=12,
            border_top_right_radius=12,
        )
    elif spec.hair_style == 2:
        # Longer side hair
        pygame.draw.rect(
            surface,
            spec.hair_color,
            (cx - head_r - 3, head_cy - head_r, 8, int(head_r * 1.5)),
            border_radius=4,
        )
        pygame.draw.rect(
            surface,
            spec.hair_color,
            (cx + head_r - 5, head_cy - head_r, 8, int(head_r * 1.5)),
            border_radius=4,
        )
        pygame.draw.rect(
            surface,
            spec.hair_color,
            (cx - head_r, head_cy - head_r - 4, head_r * 2, int(head_r * 0.55)),
            border_radius=8,
        )
    else:
        # Top bun / cap
        pygame.draw.circle(surface, spec.hair_color, (cx, head_cy - head_r - 2), max(6, head_r // 3))
        pygame.draw.rect(
            surface,
            spec.hair_color,
            (cx - head_r, head_cy - head_r - 2, head_r * 2, int(head_r * 0.45)),
            border_radius=6,
        )

    # Eyes
    eye_y = head_cy - 2
    eye_dx = max(6, int(head_r * 0.42))
    pygame.draw.circle(surface, (35, 40, 48), (cx - eye_dx, eye_y), 2)
    pygame.draw.circle(surface, (35, 40, 48), (cx + eye_dx, eye_y), 2)

    # Eyebrows
    pygame.draw.line(surface, spec.hair_color, (cx - eye_dx - 4, eye_y - 5), (cx - eye_dx + 4, eye_y - 5), 2)
    pygame.draw.line(surface, spec.hair_color, (cx + eye_dx - 4, eye_y - 5), (cx + eye_dx + 4, eye_y - 5), 2)

    # Glasses
    if spec.has_glasses:
        g_r = max(5, int(head_r * 0.28))
        pygame.draw.circle(surface, (50, 60, 75), (cx - eye_dx, eye_y), g_r, 1)
        pygame.draw.circle(surface, (50, 60, 75), (cx + eye_dx, eye_y), g_r, 1)
        pygame.draw.line(surface, (50, 60, 75), (cx - eye_dx + g_r, eye_y), (cx + eye_dx - g_r, eye_y), 1)

    # Mustache or mouth
    mouth_y = head_cy + int(head_r * 0.45)
    if spec.has_mustache:
        pygame.draw.rect(
            surface,
            spec.hair_color,
            (cx - 8, mouth_y - 4, 16, 4),
            border_radius=2,
        )
    pygame.draw.line(surface, (140, 85, 75), (cx - 5, mouth_y + 2), (cx + 5, mouth_y + 2), 2)

    pygame.draw.rect(surface, (120, 132, 148), rect, width=1, border_radius=6)


def draw_official_seal(
    surface: pygame.Surface,
    center: Tuple[int, int],
    radius: int,
    label: str,
    color: Tuple[int, int, int],
    font: pygame.font.Font,
) -> None:
    """Draw a circular bureau authentication stamp on a document card."""
    cx, cy = center
    pygame.draw.circle(surface, color, (cx, cy), radius, width=2)
    pygame.draw.circle(surface, color, (cx, cy), max(4, radius - 4), width=1)
    txt = font.render(label[:8].upper(), True, color)
    surface.blit(txt, (cx - txt.get_width() // 2, cy - txt.get_height() // 2))


def draw_star(
    surface: pygame.Surface,
    center: Tuple[int, int],
    radius: int,
    filled: bool,
    fill_color: Tuple[int, int, int] = COLOR_ACCENT_GOLD,
) -> None:
    """Draw a 5-pointed rating star."""
    cx, cy = center
    pts = []
    for i in range(10):
        angle = math.radians(i * 36 - 90)
        r = radius if i % 2 == 0 else int(radius * 0.44)
        pts.append((cx + int(math.cos(angle) * r), cy + int(math.sin(angle) * r)))
    if filled:
        pygame.draw.polygon(surface, fill_color, pts)
        pygame.draw.polygon(surface, (255, 238, 150), pts, width=1)
    else:
        pygame.draw.polygon(surface, (60, 72, 92), pts)
        pygame.draw.polygon(surface, COLOR_BORDER, pts, width=1)


def draw_world_map(
    surface: pygame.Surface,
    rect: pygame.Rect,
    countries: Dict[str, CountrySpec],
    origin_id: str,
    destination_id: str,
    transit_ids: List[str],
    font_small: pygame.font.Font,
    font_bold: pygame.font.Font,
    selected_country_id: Optional[str] = None,
) -> Dict[str, pygame.Rect]:
    """Draw a stylized flat vector map of the 6 fictional countries and return clickable node rects."""
    # Map sea background
    pygame.draw.rect(surface, (24, 38, 56), rect, border_radius=10)

    # Subtle grid lines
    for gx in range(rect.left + 40, rect.right, 60):
        pygame.draw.line(surface, (30, 46, 66), (gx, rect.top + 2), (gx, rect.bottom - 2), 1)
    for gy in range(rect.top + 40, rect.bottom, 60):
        pygame.draw.line(surface, (30, 46, 66), (rect.left + 2, gy), (rect.right - 2, gy), 1)

    # Scale original map_pos (within 820x420 virtual map canvas) to actual rect
    def to_screen(pos: Tuple[int, int]) -> Tuple[int, int]:
        nx = pos[0] / 820.0
        ny = pos[1] / 420.0
        return (
            rect.left + int(nx * rect.width),
            rect.top + int(ny * rect.height),
        )

    # Draw stylized landmass polygons around each country
    for cid, cspec in countries.items():
        sx, sy = to_screen(cspec.map_pos)
        land_col = (44, 62, 82)
        if cid == origin_id:
            land_col = (48, 78, 108)
        elif cid == destination_id:
            land_col = (46, 88, 78)
        elif cid in transit_ids:
            land_col = (88, 72, 54)
        poly = [
            (sx - 58, sy - 26),
            (sx - 18, sy - 42),
            (sx + 48, sy - 32),
            (sx + 64, sy + 12),
            (sx + 28, sy + 38),
            (sx - 44, sy + 32),
        ]
        pygame.draw.polygon(surface, land_col, poly)
        pygame.draw.polygon(surface, (66, 88, 114), poly, width=2)

    # Draw route lines: origin -> transit(s) -> destination
    route_chain = [origin_id] + list(transit_ids) + [destination_id]
    for i in range(len(route_chain) - 1):
        c_from = countries.get(route_chain[i])
        c_to = countries.get(route_chain[i + 1])
        if c_from and c_to:
            p1 = to_screen(c_from.map_pos)
            p2 = to_screen(c_to.map_pos)
            pygame.draw.line(surface, COLOR_ACCENT_GOLD, p1, p2, 3)
            # Midpoint arrow chevron
            mx = (p1[0] + p2[0]) // 2
            my = (p1[1] + p2[1]) // 2
            pygame.draw.circle(surface, COLOR_ACCENT_GOLD, (mx, my), 5)

    # Draw country nodes, flags, and labels
    node_rects: Dict[str, pygame.Rect] = {}
    for cid, cspec in countries.items():
        sx, sy = to_screen(cspec.map_pos)
        box = pygame.Rect(sx - 52, sy - 24, 104, 48)
        node_rects[cid] = box

        # Node border color by role
        border_col = COLOR_BORDER
        badge_text = ""
        if cid == origin_id:
            border_col = COLOR_ACCENT_BLUE
            badge_text = "ORIGIN"
        elif cid == destination_id:
            border_col = COLOR_SUCCESS
            badge_text = "TARGET"
        elif cid in transit_ids:
            border_col = COLOR_ACCENT_ORANGE
            badge_text = "TRANSIT"

        if cid == selected_country_id:
            pygame.draw.rect(surface, COLOR_ACCENT_GOLD, box.inflate(6, 6), width=2, border_radius=8)

        pygame.draw.rect(surface, COLOR_SHADOW, box.move(2, 3), border_radius=7)
        pygame.draw.rect(surface, COLOR_BG_DARK, box, border_radius=7)
        pygame.draw.rect(surface, border_col, box, width=2, border_radius=7)

        flag_rect = pygame.Rect(box.left + 6, box.top + 8, 28, 18)
        draw_flag(surface, flag_rect, cspec.flag)

        name_surf = font_bold.render(cspec.name, True, COLOR_TEXT_MAIN)
        surface.blit(name_surf, (flag_rect.right + 6, box.top + 8))

        if badge_text:
            b_surf = font_small.render(badge_text, True, border_col)
            surface.blit(b_surf, (box.left + 8, box.bottom - b_surf.get_height() - 4))
        else:
            fee_surf = font_small.render(f"Visa ${cspec.visa_fee}/{cspec.visa_processing_days}d", True, COLOR_TEXT_MUTED)
            surface.blit(fee_surf, (box.left + 8, box.bottom - fee_surf.get_height() - 4))

    pygame.draw.rect(surface, COLOR_BORDER, rect, width=2, border_radius=10)
    return node_rects
