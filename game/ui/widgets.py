"""Reusable modern flat UI widgets: Button, Panel, Slider, Tooltip, and DocumentCard."""

from typing import Callable, Dict, List, Optional, Set, Tuple

import pygame

from game.constants import (
    COLOR_ACCENT_BLUE,
    COLOR_ACCENT_GOLD,
    COLOR_BG_CARD,
    COLOR_BG_DARK,
    COLOR_BG_PANEL,
    COLOR_BORDER,
    COLOR_DANGER,
    COLOR_SHADOW,
    COLOR_SUCCESS,
    COLOR_TEXT_DARK,
    COLOR_TEXT_INK,
    COLOR_TEXT_MAIN,
    COLOR_TEXT_MUTED,
    DOC_HEADER_COLORS,
)
from game.core.models import CountrySpec, DocumentInstance, DocumentSpec, PortraitSpec
from game.ui.drawing import draw_flag, draw_official_seal, draw_portrait
from game.ui.theme import FontBank, wrap_text


class Button:
    """Modern flat rounded button with smooth hover/press animation and optional subtitle badge."""

    def __init__(
        self,
        rect: pygame.Rect,
        text: str,
        on_click: Optional[Callable[[], None]] = None,
        bg_color: Tuple[int, int, int] = COLOR_ACCENT_BLUE,
        text_color: Tuple[int, int, int] = COLOR_TEXT_MAIN,
        subtitle: str = "",
        enabled: bool = True,
        tooltip: str = "",
    ) -> None:
        self.rect = pygame.Rect(rect)
        self.text = text
        self.on_click = on_click
        self.bg_color = bg_color
        self.text_color = text_color
        self.subtitle = subtitle
        self.enabled = enabled
        self.tooltip = tooltip
        self.hovered: bool = False
        self.pressed: bool = False
        self.hover_anim: float = 0.0

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Process mouse hover and click events. Returns True if clicked."""
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.enabled and self.rect.collidepoint(event.pos):
                self.pressed = True
                return False
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            was_pressed = self.pressed
            self.pressed = False
            if was_pressed and self.enabled and self.rect.collidepoint(event.pos):
                if self.on_click:
                    self.on_click()
                return True
        return False

    def update(self, dt: float) -> None:
        """Animate hover brightness smoothly."""
        target = 1.0 if (self.hovered and self.enabled) else 0.0
        self.hover_anim += (target - self.hover_anim) * min(1.0, dt * 14.0)

    def draw(self, surface: pygame.Surface, fonts: FontBank) -> None:
        """Render the button with drop shadow, rounded corners, and hover tint."""
        offset_y = 2 if (self.pressed and self.enabled) else 0
        draw_rect = self.rect.move(0, offset_y)

        # Shadow
        shadow_rect = self.rect.move(0, 3)
        pygame.draw.rect(surface, COLOR_SHADOW, shadow_rect, border_radius=8)

        if self.enabled:
            boost = int(24 * self.hover_anim)
            col = (
                min(255, self.bg_color[0] + boost),
                min(255, self.bg_color[1] + boost),
                min(255, self.bg_color[2] + boost),
            )
            border_col = COLOR_ACCENT_GOLD if self.hover_anim > 0.5 else COLOR_BORDER
        else:
            col = (52, 60, 74)
            border_col = (70, 78, 92)

        pygame.draw.rect(surface, col, draw_rect, border_radius=8)
        pygame.draw.rect(surface, border_col, draw_rect, width=2, border_radius=8)

        fg = self.text_color if self.enabled else (130, 140, 155)
        if self.subtitle:
            f_main = fonts.get(16, bold=True)
            f_sub = fonts.get(13, bold=False)
            s_main = f_main.render(self.text, True, fg)
            s_sub = f_sub.render(self.subtitle, True, COLOR_ACCENT_GOLD if self.enabled else fg)
            surface.blit(s_main, (draw_rect.centerx - s_main.get_width() // 2, draw_rect.top + 7))
            surface.blit(s_sub, (draw_rect.centerx - s_sub.get_width() // 2, draw_rect.bottom - s_sub.get_height() - 6))
        else:
            f_main = fonts.get(17, bold=True)
            s_main = f_main.render(self.text, True, fg)
            surface.blit(
                s_main,
                (
                    draw_rect.centerx - s_main.get_width() // 2,
                    draw_rect.centery - s_main.get_height() // 2,
                ),
            )


class Panel:
    """Rounded flat container panel with optional header bar."""

    def __init__(
        self,
        rect: pygame.Rect,
        title: str = "",
        bg_color: Tuple[int, int, int] = COLOR_BG_PANEL,
        border_color: Tuple[int, int, int] = COLOR_BORDER,
    ) -> None:
        self.rect = pygame.Rect(rect)
        self.title = title
        self.bg_color = bg_color
        self.border_color = border_color

    def draw(self, surface: pygame.Surface, fonts: FontBank) -> None:
        """Render panel background, shadow, and optional header bar."""
        pygame.draw.rect(surface, COLOR_SHADOW, self.rect.move(0, 4), border_radius=10)
        pygame.draw.rect(surface, self.bg_color, self.rect, border_radius=10)
        if self.title:
            header_rect = pygame.Rect(self.rect.x, self.rect.y, self.rect.width, 36)
            pygame.draw.rect(
                surface,
                COLOR_BG_DARK,
                header_rect,
                border_top_left_radius=10,
                border_top_right_radius=10,
            )
            f_hdr = fonts.get(16, bold=True)
            t_surf = f_hdr.render(self.title, True, COLOR_ACCENT_GOLD)
            surface.blit(t_surf, (header_rect.x + 14, header_rect.centery - t_surf.get_height() // 2))
        pygame.draw.rect(surface, self.border_color, self.rect, width=2, border_radius=10)


class Slider:
    """Horizontal numeric slider widget for audio volume or UI scale settings."""

    def __init__(
        self,
        rect: pygame.Rect,
        label: str,
        value: float,
        min_val: float = 0.0,
        max_val: float = 1.0,
        on_change: Optional[Callable[[float], None]] = None,
    ) -> None:
        self.rect = pygame.Rect(rect)
        self.label = label
        self.value = value
        self.min_val = min_val
        self.max_val = max_val
        self.on_change = on_change
        self.dragging = False

    def _track_rect(self) -> pygame.Rect:
        return pygame.Rect(self.rect.x, self.rect.bottom - 16, self.rect.width, 10)

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handle mouse drag on the slider track."""
        track = self._track_rect().inflate(10, 14)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if track.collidepoint(event.pos):
                self.dragging = True
                self._update_from_x(event.pos[0])
                return True
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self._update_from_x(event.pos[0])
            return True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.dragging:
                self.dragging = False
                return True
        return False

    def _update_from_x(self, mouse_x: int) -> None:
        track = self._track_rect()
        ratio = max(0.0, min(1.0, (mouse_x - track.left) / max(1, track.width)))
        self.value = self.min_val + ratio * (self.max_val - self.min_val)
        if self.on_change:
            self.on_change(self.value)

    def draw(self, surface: pygame.Surface, fonts: FontBank) -> None:
        """Render label, percentage, track, and thumb."""
        f_lbl = fonts.get(16, bold=True)
        pct = int(round(((self.value - self.min_val) / max(0.001, self.max_val - self.min_val)) * 100))
        lbl_surf = f_lbl.render(f"{self.label}: {pct}%", True, COLOR_TEXT_MAIN)
        surface.blit(lbl_surf, (self.rect.x, self.rect.y))

        track = self._track_rect()
        pygame.draw.rect(surface, COLOR_BG_DARK, track, border_radius=5)
        ratio = (self.value - self.min_val) / max(0.001, self.max_val - self.min_val)
        fill_w = int(track.width * max(0.0, min(1.0, ratio)))
        if fill_w > 0:
            pygame.draw.rect(
                surface,
                COLOR_ACCENT_BLUE,
                pygame.Rect(track.x, track.y, fill_w, track.height),
                border_radius=5,
            )
        pygame.draw.rect(surface, COLOR_BORDER, track, width=1, border_radius=5)
        thumb_x = track.x + fill_w
        pygame.draw.circle(surface, COLOR_ACCENT_GOLD, (thumb_x, track.centery), 9)
        pygame.draw.circle(surface, COLOR_BG_DARK, (thumb_x, track.centery), 9, width=2)


class Tooltip:
    """Floating tooltip box that renders near the cursor when hovering interactive elements."""

    def draw(
        self,
        surface: pygame.Surface,
        text: str,
        pos: Tuple[int, int],
        fonts: FontBank,
    ) -> None:
        """Render a multi-line tooltip near pos, clamped inside screen bounds."""
        if not text:
            return
        font = fonts.get(14)
        lines = wrap_text(text, font, 280)
        if not lines:
            return
        w = max(font.size(line)[0] for line in lines) + 20
        h = len(lines) * (font.get_linesize() + 2) + 14

        sw, sh = surface.get_size()
        x = min(sw - w - 10, max(10, pos[0] + 14))
        y = min(sh - h - 10, max(10, pos[1] + 14))
        box = pygame.Rect(x, y, w, h)

        pygame.draw.rect(surface, COLOR_SHADOW, box.move(2, 3), border_radius=6)
        pygame.draw.rect(surface, (20, 26, 36), box, border_radius=6)
        pygame.draw.rect(surface, COLOR_ACCENT_GOLD, box, width=1, border_radius=6)

        cy = box.top + 7
        for line in lines:
            s = font.render(line, True, COLOR_TEXT_MAIN)
            surface.blit(s, (box.left + 10, cy))
            cy += font.get_linesize() + 2


class DocumentCard:
    """Procedural paper document card on the Consul or Traveler desk with clickable fields."""

    def __init__(
        self,
        rect: pygame.Rect,
        doc: DocumentInstance,
        doc_spec: DocumentSpec,
        countries: Dict[str, CountrySpec],
        portrait: Optional[PortraitSpec] = None,
        interactive_fields: bool = True,
    ) -> None:
        self.rect = pygame.Rect(rect)
        self.doc = doc
        self.doc_spec = doc_spec
        self.countries = countries
        self.portrait = portrait
        self.interactive_fields = interactive_fields
        self.field_rects: Dict[str, Tuple[pygame.Rect, str]] = {}

    def _country_name(self, cid: str) -> str:
        if not cid:
            return "All Zones"
        c = self.countries.get(cid)
        return c.name if c else cid.title()

    def get_hovered_field(self, pos: Tuple[int, int]) -> Optional[Tuple[str, str]]:
        """Return (field_name, tooltip_text) if pos is over a clickable document field."""
        if not self.rect.collidepoint(pos):
            return None
        for fname, (frect, tip) in self.field_rects.items():
            if frect.collidepoint(pos):
                return fname, tip
        return None

    def draw(
        self,
        surface: pygame.Surface,
        fonts: FontBank,
        flagged_fields: Optional[Set[Tuple[str, str]]] = None,
        current_day: int = 1,
    ) -> None:
        """Draw the paper document card, header ribbon, fields, stamp seal, and discrepancy flags."""
        self.field_rects.clear()
        flags = flagged_fields or set()

        # Shadow & paper base
        pygame.draw.rect(surface, COLOR_SHADOW, self.rect.move(3, 4), border_radius=8)
        pygame.draw.rect(surface, COLOR_BG_CARD, self.rect, border_radius=8)

        # Colored header bar
        hdr_color = DOC_HEADER_COLORS.get(self.doc.doc_type, (60, 80, 110))
        hdr_rect = pygame.Rect(self.rect.x, self.rect.y, self.rect.width, 30)
        pygame.draw.rect(
            surface,
            hdr_color,
            hdr_rect,
            border_top_left_radius=8,
            border_top_right_radius=8,
        )

        f_hdr = fonts.get(14, bold=True)
        f_lbl = fonts.get(12, bold=False)
        f_val = fonts.get(13, bold=True)
        f_mono = fonts.get(11, bold=True, mono=True)

        title_surf = f_hdr.render(self.doc_spec.name.upper(), True, COLOR_TEXT_MAIN)
        surface.blit(title_surf, (hdr_rect.x + 10, hdr_rect.centery - title_surf.get_height() // 2))

        # Optional small flag in header
        flag_cid = self.doc.target_country or self.doc.nationality
        if flag_cid in self.countries:
            f_rect = pygame.Rect(hdr_rect.right - 34, hdr_rect.y + 6, 26, 17)
            draw_flag(surface, f_rect, self.countries[flag_cid].flag)

        content_x = self.rect.x + 10
        content_y = hdr_rect.bottom + 8

        # If passport and portrait is provided, draw miniature photo on left
        if self.doc.doc_type == "passport" and self.portrait is not None:
            p_rect = pygame.Rect(content_x, content_y, 52, 64)
            draw_portrait(surface, p_rect, self.portrait)
            content_x += 60

        # Build fields list: (field_key, display_label, display_value, tooltip)
        rows: List[Tuple[str, str, str, str]] = [
            (
                "owner_name",
                "Holder:",
                self.doc.owner_name,
                "Click to flag if the document holder's name does not match the applicant.",
            ),
        ]

        if self.doc_spec.target_country_specific:
            rows.append(
                (
                    "target_country",
                    "Valid For:",
                    self._country_name(self.doc.target_country),
                    "Click to flag if this document was issued for the wrong destination/transit country.",
                )
            )
        else:
            rows.append(
                (
                    "nationality",
                    "Origin:",
                    self._country_name(self.doc.nationality),
                    "Issuing nationality of the document holder.",
                )
            )

        rows.append(
            (
                "expiry_day",
                "Expires:",
                f"Day {self.doc.expiry_day} (Issued D{self.doc.issue_day})",
                "Click to flag if expired or if passport validity buffer is too short.",
            )
        )

        if self.doc.doc_type == "bank_statement":
            bal = self.doc.extra_data.get("balance", 0)
            rows.append(
                (
                    "balance",
                    "Balance:",
                    f"${bal} Certified Reserve",
                    "Click to flag if bank balance is below the destination country's minimum.",
                )
            )

        row_w = self.rect.right - content_x - 8
        for f_key, lbl, val, tip in rows:
            r_rect = pygame.Rect(content_x, content_y, row_w, 22)
            self.field_rects[f_key] = (r_rect, tip)

            is_flagged = (self.doc.doc_type, f_key) in flags
            if is_flagged:
                pygame.draw.rect(surface, (254, 215, 215), r_rect, border_radius=4)
                pygame.draw.rect(surface, COLOR_DANGER, r_rect, width=1, border_radius=4)

            lbl_s = f_lbl.render(lbl, True, (100, 110, 125))
            surface.blit(lbl_s, (r_rect.x + 2, r_rect.y + 3))

            val_color = COLOR_DANGER if is_flagged else COLOR_TEXT_INK
            if f_key == "expiry_day" and self.doc.expiry_day < current_day and not self.interactive_fields:
                val_color = COLOR_DANGER
            val_s = f_val.render(val, True, val_color)
            surface.blit(val_s, (r_rect.x + 62, r_rect.y + 2))
            content_y += 24

        # Stamp / Seal box in bottom-right corner
        stamp_rect = pygame.Rect(self.rect.right - 92, self.rect.bottom - 44, 84, 38)
        self.field_rects["stamped"] = (
            stamp_rect,
            "Official authentication stamp. Click to flag if the stamp is missing!",
        )
        stamp_flagged = (self.doc.doc_type, "stamped") in flags
        if stamp_flagged:
            pygame.draw.rect(surface, (254, 215, 215), stamp_rect, border_radius=5)
            pygame.draw.rect(surface, COLOR_DANGER, stamp_rect, width=2, border_radius=5)

        if self.doc.stamped:
            draw_official_seal(
                surface,
                stamp_rect.center,
                16,
                self.doc_spec.short_name,
                hdr_color,
                f_mono,
            )
        else:
            pygame.draw.rect(surface, (190, 180, 165), stamp_rect, width=1, border_radius=4)
            no_s = f_mono.render("NO STAMP", True, (165, 95, 95))
            surface.blit(no_s, (stamp_rect.centerx - no_s.get_width() // 2, stamp_rect.centery - no_s.get_height() // 2))

        # Signature line on bottom-left
        sig_y = self.rect.bottom - 14
        pygame.draw.line(surface, (170, 165, 155), (self.rect.x + 12, sig_y), (self.rect.right - 102, sig_y), 1)
        sig_txt = f_lbl.render(self.doc_spec.issuer[:22], True, (120, 125, 135))
        surface.blit(sig_txt, (self.rect.x + 12, sig_y - 15))

        pygame.draw.rect(surface, (160, 152, 138), self.rect, width=2, border_radius=8)
