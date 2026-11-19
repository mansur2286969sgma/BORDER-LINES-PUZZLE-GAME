"""Traveler Campaign gameplay screen: stylized world map, calendar, money counter, agency buttons, and dossier."""

from typing import Dict, List, Optional, TYPE_CHECKING

import pygame

from game.campaigns.traveler import TravelerActionSpec, TravelerSession
from game.constants import (
    COLOR_ACCENT_BLUE,
    COLOR_ACCENT_GOLD,
    COLOR_ACCENT_ORANGE,
    COLOR_ACCENT_PURPLE,
    COLOR_ACCENT_TEAL,
    COLOR_BG_DARK,
    COLOR_BG_MAIN,
    COLOR_BG_PANEL,
    COLOR_BG_PANEL_ALT,
    COLOR_BORDER,
    COLOR_DANGER,
    COLOR_DANGER_DARK,
    COLOR_SUCCESS,
    COLOR_SUCCESS_DARK,
    COLOR_TEXT_MAIN,
    COLOR_TEXT_MUTED,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)
from game.core.models import TravelerLevelSpec
from game.ui.drawing import draw_world_map
from game.ui.effects import ParticleSystem
from game.ui.screens import BaseScreen
from game.ui.theme import draw_text_wrapped
from game.ui.widgets import Button, DocumentCard, Panel, Tooltip

if TYPE_CHECKING:
    from game.app import Game


class TravelerScreen(BaseScreen):
    """Interactive gameplay screen for the Traveler Campaign."""

    def __init__(self, app: "Game") -> None:
        super().__init__(app)
        self.session: Optional[TravelerSession] = None
        self.action_buttons: List[Tuple[Button, TravelerActionSpec]] = []
        self.top_buttons: List[Button] = []
        self.pause_buttons: List[Button] = []
        self.doc_cards: List[DocumentCard] = []
        self.country_node_rects: Dict[str, pygame.Rect] = {}
        self.selected_country_id: str = ""
        self.show_intro_modal: bool = True
        self.paused: bool = False
        self.particles = ParticleSystem()
        self.tooltip = Tooltip()

        self.intro_start_btn = Button(
            pygame.Rect(SCREEN_WIDTH // 2 - 120, 495, 240, 48),
            "START PLANNING",
            on_click=self._dismiss_intro,
            bg_color=COLOR_SUCCESS_DARK,
        )

    def load_level(self, level: TravelerLevelSpec) -> None:
        """Initialize a new TravelerSession for level."""
        self.session = TravelerSession(level, self.app.engine)
        self.selected_country_id = level.destination
        self.show_intro_modal = True
        self.paused = False
        self.particles.clear()
        self._build_top_buttons()
        self._build_pause_buttons()
        self._rebuild_action_buttons()
        self._rebuild_doc_cards()

    def _dismiss_intro(self) -> None:
        self.app.audio.play("click")
        self.show_intro_modal = False

    def _build_top_buttons(self) -> None:
        self.top_buttons = [
            Button(
                pygame.Rect(SCREEN_WIDTH - 340, 11, 100, 36),
                "Hint [H]",
                on_click=self._on_hint,
                bg_color=COLOR_ACCENT_PURPLE,
                tooltip="Reveal a helpful tip for solving this level.",
            ),
            Button(
                pygame.Rect(SCREEN_WIDTH - 230, 11, 105, 36),
                "Restart [R]",
                on_click=self._on_restart,
                bg_color=COLOR_BG_PANEL_ALT,
                tooltip="Instantly restart this level from Day 1.",
            ),
            Button(
                pygame.Rect(SCREEN_WIDTH - 115, 11, 95, 36),
                "Pause [Esc]",
                on_click=self._toggle_pause,
                bg_color=COLOR_BG_PANEL_ALT,
            ),
        ]

    def _build_pause_buttons(self) -> None:
        cx = SCREEN_WIDTH // 2
        self.pause_buttons = [
            Button(pygame.Rect(cx - 140, 270, 280, 48), "RESUME", on_click=self._toggle_pause, bg_color=COLOR_ACCENT_BLUE),
            Button(pygame.Rect(cx - 140, 332, 280, 48), "RESTART LEVEL", on_click=self._on_restart, bg_color=COLOR_ACCENT_TEAL),
            Button(pygame.Rect(cx - 140, 394, 280, 48), "LEVEL SELECT", on_click=self._on_exit_to_select, bg_color=COLOR_BG_PANEL_ALT),
            Button(pygame.Rect(cx - 140, 456, 280, 48), "MAIN MENU", on_click=self._on_exit_to_menu, bg_color=COLOR_DANGER_DARK),
        ]

    def _rebuild_action_buttons(self) -> None:
        self.action_buttons.clear()
        if not self.session:
            return
        specs = self.session.get_action_specs()
        panel_x = 815
        start_y = 104
        btn_w = 430
        btn_h = 46
        gap = 52

        for idx, spec in enumerate(specs):
            can_do, reason = self.session.can_perform_action(spec)
            if spec.action_id == "travel":
                bg = COLOR_SUCCESS_DARK
                sub = "Present Dossier at Border Control"
            elif spec.action_id == "wait_day":
                bg = COLOR_BG_PANEL_ALT
                sub = "+1 Day  •  $0"
            else:
                bg = COLOR_ACCENT_BLUE
                sub = f"Time: +{spec.days_cost}d   •   Fee: ${spec.money_cost}"

            act_id = spec.action_id
            btn = Button(
                pygame.Rect(panel_x, start_y + idx * gap, btn_w, btn_h),
                spec.label,
                on_click=lambda aid=act_id: self._on_execute_action(aid),
                bg_color=bg,
                subtitle=sub,
                enabled=can_do,
                tooltip=f"{spec.description}\nStatus: {reason}",
            )
            self.action_buttons.append((btn, spec))

    def _rebuild_doc_cards(self) -> None:
        self.doc_cards.clear()
        if not self.session:
            return
        docs = self.session.state.documents
        start_x = 32
        y = 534
        card_w = 232
        card_h = 158
        gap = 12
        for idx, doc in enumerate(docs):
            doc_spec = self.app.db.documents[doc.doc_type]
            rect = pygame.Rect(start_x + idx * (card_w + gap), y, card_w, card_h)
            self.doc_cards.append(
                DocumentCard(
                    rect=rect,
                    doc=doc,
                    doc_spec=doc_spec,
                    countries=self.app.db.countries,
                    interactive_fields=False,
                )
            )

    def _on_execute_action(self, action_id: str) -> None:
        if not self.session:
            return
        outcome = self.session.execute_action(action_id)
        if outcome.travel_triggered:
            if outcome.success:
                self.app.audio.play("success")
                self.app.progress.record_traveler_completion(
                    self.session.level.id, self.session.stars_earned
                )
            else:
                self.app.audio.play("error")
            self.app.show_traveler_results(self.session)
            return

        if outcome.success:
            if action_id == "wait_day":
                self.app.audio.play("page")
            else:
                self.app.audio.play("stamp")
                self.particles.spawn_stamp_sparks(980, 320, "ISSUED", True)
            self._rebuild_action_buttons()
            self._rebuild_doc_cards()
        else:
            self.app.audio.play("error")

    def _on_hint(self) -> None:
        if not self.session:
            return
        self.app.audio.play("coin")
        self.session.reveal_next_hint()

    def _on_restart(self) -> None:
        if not self.session:
            return
        self.app.audio.play("page")
        self.session.restart()
        self.paused = False
        self.show_intro_modal = False
        self._rebuild_action_buttons()
        self._rebuild_doc_cards()

    def _toggle_pause(self) -> None:
        self.app.audio.play("click")
        self.paused = not self.paused

    def _on_exit_to_select(self) -> None:
        self.app.audio.play("click")
        self.app.open_level_select("traveler")

    def _on_exit_to_menu(self) -> None:
        self.app.audio.play("click")
        self.app.change_screen("menu")

    def handle_event(self, event: pygame.event.Event) -> None:
        """Process keyboard shortcuts and mouse interactions."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.show_intro_modal:
                    self._dismiss_intro()
                else:
                    self._toggle_pause()
                return
            if event.key == pygame.K_r and not self.paused:
                self._on_restart()
                return
            if event.key == pygame.K_h and not self.paused and not self.show_intro_modal:
                self._on_hint()
                return

        if self.paused:
            for b in self.pause_buttons:
                b.handle_event(event)
            return

        if self.show_intro_modal:
            self.intro_start_btn.handle_event(event)
            return

        for b in self.top_buttons:
            b.handle_event(event)
        for b, _ in self.action_buttons:
            b.handle_event(event)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for cid, nrect in self.country_node_rects.items():
                if nrect.collidepoint(event.pos):
                    self.selected_country_id = cid
                    self.app.audio.play("click")
                    break

    def update(self, dt: float) -> None:
        """Advance particles and button animations."""
        self.particles.update(dt)
        if self.paused:
            for b in self.pause_buttons:
                b.update(dt)
            return
        if self.show_intro_modal:
            self.intro_start_btn.update(dt)
            return
        for b in self.top_buttons:
            b.update(dt)
        for b, _ in self.action_buttons:
            b.update(dt)

    def draw(self, surface: pygame.Surface) -> None:
        """Render the Traveler Campaign interface: top bar, world map, agency actions, and held documents."""
        surface.fill(COLOR_BG_MAIN)
        if not self.session:
            return

        st = self.session.state
        lvl = self.session.level

        # 1. Top status bar
        pygame.draw.rect(surface, COLOR_BG_DARK, pygame.Rect(0, 0, SCREEN_WIDTH, 58))
        pygame.draw.line(surface, COLOR_BORDER, (0, 58), (SCREEN_WIDTH, 58), 2)

        f_hdr = self.app.fonts.get(20, bold=True)
        f_stat = self.app.fonts.get(17, bold=True)
        f_small = self.app.fonts.get(13)
        f_bold = self.app.fonts.get(14, bold=True)

        title_s = f_hdr.render(f"Level {lvl.id}: {lvl.title}", True, COLOR_ACCENT_GOLD)
        surface.blit(title_s, (24, 16))

        # Calendar widget
        day_col = COLOR_DANGER if st.current_day > st.deadline_day else COLOR_TEXT_MAIN
        cal_box = pygame.Rect(310, 10, 210, 38)
        pygame.draw.rect(surface, COLOR_BG_PANEL, cal_box, border_radius=6)
        pygame.draw.rect(surface, COLOR_BORDER, cal_box, width=1, border_radius=6)
        cal_s = f_stat.render(f"DAY {st.current_day} / Deadline D{st.deadline_day}", True, day_col)
        surface.blit(cal_s, (cal_box.centerx - cal_s.get_width() // 2, cal_box.centery - cal_s.get_height() // 2))

        # Budget widget
        bud_box = pygame.Rect(535, 10, 175, 38)
        pygame.draw.rect(surface, COLOR_BG_PANEL, bud_box, border_radius=6)
        pygame.draw.rect(surface, COLOR_BORDER, bud_box, width=1, border_radius=6)
        bud_s = f_stat.render(f"BUDGET: ${st.budget}", True, COLOR_SUCCESS if st.budget >= 20 else COLOR_ACCENT_ORANGE)
        surface.blit(bud_s, (bud_box.centerx - bud_s.get_width() // 2, bud_box.centery - bud_s.get_height() // 2))

        # Bank Reserve badge
        res_box = pygame.Rect(720, 10, 195, 38)
        pygame.draw.rect(surface, COLOR_BG_PANEL, res_box, border_radius=6)
        pygame.draw.rect(surface, COLOR_BORDER, res_box, width=1, border_radius=6)
        res_s = f_bold.render(f"Bank Reserve: ${st.declared_bank_balance}", True, COLOR_TEXT_MUTED)
        surface.blit(res_s, (res_box.centerx - res_s.get_width() // 2, res_box.centery - res_s.get_height() // 2))

        for b in self.top_buttons:
            b.draw(surface, self.app.fonts)

        # 2. Left Panel: World Map & Selected Country Rules
        map_panel = Panel(pygame.Rect(20, 68, 770, 422), title="CONTINENTAL TRANSIT MAP (Click a Country to Inspect Rules)")
        map_panel.draw(surface, self.app.fonts)

        map_canvas_rect = pygame.Rect(32, 112, 746, 265)
        self.country_node_rects = draw_world_map(
            surface=surface,
            rect=map_canvas_rect,
            countries=self.app.db.countries,
            origin_id=lvl.origin,
            destination_id=lvl.destination,
            transit_ids=list(lvl.transit_countries),
            font_small=self.app.fonts.get(11),
            font_bold=self.app.fonts.get(13, bold=True),
            selected_country_id=self.selected_country_id,
        )

        # Country Rule Summary Strip below map
        info_rect = pygame.Rect(32, 384, 746, 96)
        pygame.draw.rect(surface, COLOR_BG_DARK, info_rect, border_radius=8)
        pygame.draw.rect(surface, COLOR_BORDER, info_rect, width=1, border_radius=8)

        sel_country = self.app.db.countries.get(self.selected_country_id or lvl.destination)
        if sel_country:
            req_names = [self.app.db.documents[d].name for d in sel_country.required_documents if d in self.app.db.documents]
            prereq_names = [self.app.db.documents[d].name for d in sel_country.visa_prerequisites if d in self.app.db.documents]
            c_hdr = f_bold.render(
                f"{sel_country.name.upper()} ENTRY REQUIREMENTS — \"{sel_country.motto}\"",
                True,
                COLOR_ACCENT_GOLD,
            )
            surface.blit(c_hdr, (info_rect.x + 12, info_rect.y + 8))

            line1 = (
                f"• Required Dossier: {', '.join(req_names)}   |   "
                f"Passport Buffer: {sel_country.passport_min_validity_days}+ days past arrival"
            )
            line2 = (
                f"• Visa Fee: ${sel_country.visa_fee} ({sel_country.visa_processing_days}d)   |   "
                f"Visa Prerequisites: {', '.join(prereq_names)}   |   Min Bank Reserve: ${sel_country.min_bank_balance}"
            )
            s1 = f_small.render(line1, True, COLOR_TEXT_MAIN)
            s2 = f_small.render(line2, True, COLOR_TEXT_MUTED)
            surface.blit(s1, (info_rect.x + 12, info_rect.y + 34))
            surface.blit(s2, (info_rect.x + 12, info_rect.y + 56))

        # Goal & Latest Log banner
        if self.session.status_log:
            latest_log = self.session.status_log[-1]
            s_log = f_bold.render(f"Bureau Log: {latest_log}", True, COLOR_ACCENT_BLUE)
            surface.blit(s_log, (info_rect.x + 12, info_rect.y + 75))

        # 3. Right Panel: Agency Actions
        agency_panel = Panel(pygame.Rect(800, 68, 460, 422), title="CITY BUREAU & TRAVEL AGENCY")
        agency_panel.draw(surface, self.app.fonts)

        hovered_tip = ""
        for b, _ in self.action_buttons:
            b.draw(surface, self.app.fonts)
            if b.hovered and b.tooltip:
                hovered_tip = b.tooltip
        for b in self.top_buttons:
            if b.hovered and b.tooltip:
                hovered_tip = b.tooltip

        # 4. Bottom Panel: Traveler's Current Document Dossier
        dossier_panel = Panel(
            pygame.Rect(20, 498, SCREEN_WIDTH - 40, 206),
            title=f"TRAVELER DOSSIER — {st.name.upper()} (Origin: {self.app.db.countries[st.origin].name})",
        )
        dossier_panel.draw(surface, self.app.fonts)

        for card in self.doc_cards:
            card.draw(surface, self.app.fonts, current_day=st.current_day)

        self.particles.draw(surface, self.app.fonts.get(18, bold=True))

        # 5. Intro briefing modal
        if self.show_intro_modal:
            self._draw_intro_modal(surface)
        elif self.paused:
            self._draw_pause_modal(surface)
        elif hovered_tip:
            self.tooltip.draw(surface, hovered_tip, pygame.mouse.get_pos(), self.app.fonts)

    def _draw_intro_modal(self, surface: pygame.Surface) -> None:
        if not self.session:
            return
        lvl = self.session.level
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((10, 14, 22, 195))
        surface.blit(overlay, (0, 0))

        box = pygame.Rect(SCREEN_WIDTH // 2 - 330, 130, 660, 440)
        modal = Panel(box, title=f"MISSION BRIEFING — LEVEL {lvl.id}: {lvl.title.upper()}")
        modal.draw(surface, self.app.fonts)

        f_sub = self.app.fonts.get(18, bold=True)
        f_body = self.app.fonts.get(16)
        f_goal = self.app.fonts.get(16, bold=True)

        sub_s = f_sub.render(lvl.subtitle, True, COLOR_ACCENT_GOLD)
        surface.blit(sub_s, (box.x + 28, box.y + 54))

        draw_text_wrapped(
            surface,
            lvl.intro_text,
            f_body,
            COLOR_TEXT_MAIN,
            pygame.Rect(box.x + 28, box.y + 92, box.width - 56, 170),
            line_spacing=6,
        )

        goal_box = pygame.Rect(box.x + 28, box.y + 270, box.width - 56, 76)
        pygame.draw.rect(surface, COLOR_BG_DARK, goal_box, border_radius=8)
        pygame.draw.rect(surface, COLOR_ACCENT_BLUE, goal_box, width=1, border_radius=8)

        g_hdr = f_goal.render("OBJECTIVE & ROUTE:", True, COLOR_ACCENT_BLUE)
        surface.blit(g_hdr, (goal_box.x + 14, goal_box.y + 10))
        draw_text_wrapped(
            surface,
            lvl.goal_text,
            f_body,
            COLOR_TEXT_MAIN,
            pygame.Rect(goal_box.x + 14, goal_box.y + 36, goal_box.width - 28, 36),
        )

        self.intro_start_btn.draw(surface, self.app.fonts)

    def _draw_pause_modal(self, surface: pygame.Surface) -> None:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((10, 14, 22, 195))
        surface.blit(overlay, (0, 0))

        box = pygame.Rect(SCREEN_WIDTH // 2 - 200, 200, 400, 330)
        modal = Panel(box, title="GAME PAUSED")
        modal.draw(surface, self.app.fonts)
        for b in self.pause_buttons:
            b.draw(surface, self.app.fonts)
