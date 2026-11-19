"""Consul Campaign gameplay screen: top-down inspection desk, clickable paper cards, rulebook slide-out, and stamps."""

from typing import List, Optional, Tuple, TYPE_CHECKING

import pygame

from game.campaigns.consul import ConsulDecisionOutcome, ConsulSession
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
    COLOR_DESK_MAT,
    COLOR_DESK_WOOD,
    COLOR_SUCCESS,
    COLOR_SUCCESS_DARK,
    COLOR_TEXT_MAIN,
    COLOR_TEXT_MUTED,
    DECISION_APPROVE,
    DECISION_DENY,
    DECISION_REQUEST_DOC,
    DENIAL_REASON_LABELS,
    REASON_EXPIRED,
    REASON_INSUFFICIENT_FUNDS,
    REASON_INSUFFICIENT_VALIDITY,
    REASON_MISSING_PREREQUISITE,
    REASON_MISSING_STAMP,
    REASON_WRONG_COUNTRY,
    REASON_WRONG_NAME,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)
from game.core.models import ConsulShiftSpec
from game.ui.drawing import draw_flag, draw_portrait
from game.ui.effects import ParticleSystem, ease_out_cubic
from game.ui.screens import BaseScreen
from game.ui.theme import draw_text_wrapped
from game.ui.widgets import Button, DocumentCard, Panel, Tooltip

if TYPE_CHECKING:
    from game.app import Game


class ConsulScreen(BaseScreen):
    """Interactive consular desk gameplay screen for the Consul Campaign."""

    def __init__(self, app: "Game") -> None:
        super().__init__(app)
        self.session: Optional[ConsulSession] = None
        self.doc_cards: List[DocumentCard] = []
        self.top_buttons: List[Button] = []
        self.stamp_buttons: List[Button] = []
        self.reason_buttons: List[Tuple[Button, str]] = []
        self.pause_buttons: List[Button] = []

        self.rulebook_open: bool = True
        self.rulebook_anim: float = 1.0
        self.show_deny_modal: bool = False
        self.show_intro_modal: bool = True
        self.paused: bool = False
        self.feedback_banner: Optional[ConsulDecisionOutcome] = None
        self.feedback_timer: float = 0.0

        self.particles = ParticleSystem()
        self.tooltip = Tooltip()

        self.intro_start_btn = Button(
            pygame.Rect(SCREEN_WIDTH // 2 - 120, 520, 240, 48),
            "OPEN BOOTH WINDOW",
            on_click=self._dismiss_intro,
            bg_color=COLOR_SUCCESS_DARK,
        )
        self.cancel_deny_btn = Button(
            pygame.Rect(SCREEN_WIDTH // 2 - 90, 525, 180, 42),
            "Cancel",
            on_click=self._close_deny_modal,
            bg_color=COLOR_BG_PANEL_ALT,
        )

    def load_shift(self, shift: ConsulShiftSpec) -> None:
        """Initialize a new ConsulSession for shift."""
        self.session = ConsulSession(shift, self.app.engine)
        self.rulebook_open = True
        self.rulebook_anim = 1.0
        self.show_deny_modal = False
        self.show_intro_modal = True
        self.paused = False
        self.feedback_banner = None
        self.feedback_timer = 0.0
        self.particles.clear()
        self._build_top_buttons()
        self._build_stamp_buttons()
        self._build_reason_buttons()
        self._build_pause_buttons()
        self._rebuild_applicant_cards()

    def _dismiss_intro(self) -> None:
        self.app.audio.play("click")
        self.show_intro_modal = False

    def _close_deny_modal(self) -> None:
        self.app.audio.play("click")
        self.show_deny_modal = False

    def _build_top_buttons(self) -> None:
        self.top_buttons = [
            Button(
                pygame.Rect(SCREEN_WIDTH - 365, 11, 130, 36),
                "Rulebook [Tab]",
                on_click=self._toggle_rulebook,
                bg_color=COLOR_ACCENT_PURPLE,
                tooltip="Slide the Consular Rulebook panel in or out.",
            ),
            Button(
                pygame.Rect(SCREEN_WIDTH - 225, 11, 105, 36),
                "Restart [R]",
                on_click=self._on_restart,
                bg_color=COLOR_BG_PANEL_ALT,
                tooltip="Restart the current shift from the first applicant.",
            ),
            Button(
                pygame.Rect(SCREEN_WIDTH - 110, 11, 95, 36),
                "Pause [Esc]",
                on_click=self._toggle_pause,
                bg_color=COLOR_BG_PANEL_ALT,
            ),
        ]

    def _build_stamp_buttons(self) -> None:
        self.stamp_buttons = [
            Button(
                pygame.Rect(330, SCREEN_HEIGHT - 74, 210, 54),
                "STAMP: APPROVE",
                on_click=self._on_approve_clicked,
                bg_color=COLOR_SUCCESS_DARK,
                subtitle="Grant Border Entry",
                tooltip="Approve this applicant if all required documents are present and valid.",
            ),
            Button(
                pygame.Rect(555, SCREEN_HEIGHT - 74, 210, 54),
                "STAMP: DENY...",
                on_click=self._on_deny_clicked,
                bg_color=COLOR_DANGER_DARK,
                subtitle="Reject & Cite Violation",
                tooltip="Deny entry and choose the rule violation (or flag the discrepancy field directly).",
            ),
            Button(
                pygame.Rect(780, SCREEN_HEIGHT - 74, 250, 54),
                "REQUEST MISSING DOC",
                on_click=self._on_request_doc_clicked,
                bg_color=COLOR_ACCENT_ORANGE,
                text_color=(25, 30, 40),
                subtitle="Return for Incomplete Packet",
                tooltip="Use when a required document (e.g., Visa, Insurance, Transit Permit) is completely missing from the desk.",
            ),
        ]

    def _build_reason_buttons(self) -> None:
        self.reason_buttons.clear()
        reasons = [
            REASON_EXPIRED,
            REASON_INSUFFICIENT_VALIDITY,
            REASON_WRONG_NAME,
            REASON_WRONG_COUNTRY,
            REASON_MISSING_STAMP,
            REASON_INSUFFICIENT_FUNDS,
            REASON_MISSING_PREREQUISITE,
        ]
        cx = SCREEN_WIDTH // 2
        start_y = 200
        btn_w = 420
        btn_h = 40
        gap = 45
        for idx, r_code in enumerate(reasons):
            label = DENIAL_REASON_LABELS.get(r_code, r_code)
            code_copy = r_code
            btn = Button(
                pygame.Rect(cx - btn_w // 2, start_y + idx * gap, btn_w, btn_h),
                label,
                on_click=lambda rc=code_copy: self._submit_denial_with_reason(rc),
                bg_color=COLOR_DANGER_DARK,
            )
            self.reason_buttons.append((btn, r_code))

    def _build_pause_buttons(self) -> None:
        cx = SCREEN_WIDTH // 2
        self.pause_buttons = [
            Button(pygame.Rect(cx - 140, 270, 280, 48), "RESUME", on_click=self._toggle_pause, bg_color=COLOR_ACCENT_BLUE),
            Button(pygame.Rect(cx - 140, 332, 280, 48), "RESTART SHIFT", on_click=self._on_restart, bg_color=COLOR_ACCENT_TEAL),
            Button(pygame.Rect(cx - 140, 394, 280, 48), "SHIFT SELECT", on_click=self._on_exit_to_select, bg_color=COLOR_BG_PANEL_ALT),
            Button(pygame.Rect(cx - 140, 456, 280, 48), "MAIN MENU", on_click=self._on_exit_to_menu, bg_color=COLOR_DANGER_DARK),
        ]

    def _rebuild_applicant_cards(self) -> None:
        self.doc_cards.clear()
        if not self.session or not self.session.current_applicant:
            return
        app_case = self.session.current_applicant
        desk_x = 325
        desk_y = 92
        card_w = 278
        card_h = 172
        gap_x = 18
        gap_y = 16

        for idx, doc in enumerate(app_case.documents):
            col = idx % 2
            row = idx // 2
            rect = pygame.Rect(
                desk_x + col * (card_w + gap_x),
                desk_y + row * (card_h + gap_y),
                card_w,
                card_h,
            )
            doc_spec = self.app.db.documents[doc.doc_type]
            self.doc_cards.append(
                DocumentCard(
                    rect=rect,
                    doc=doc,
                    doc_spec=doc_spec,
                    countries=self.app.db.countries,
                    portrait=app_case.portrait if doc.doc_type == "passport" else None,
                    interactive_fields=True,
                )
            )

    def _toggle_rulebook(self) -> None:
        self.app.audio.play("page")
        self.rulebook_open = not self.rulebook_open

    def _on_approve_clicked(self) -> None:
        if not self.session or self.session.finished:
            return
        self.app.audio.play("stamp")
        self.particles.spawn_stamp_sparks(580, 320, "APPROVED", True)
        outcome = self.session.submit_decision(DECISION_APPROVE)
        self._after_decision(outcome)

    def _on_deny_clicked(self) -> None:
        if not self.session or self.session.finished:
            return
        self.app.audio.play("click")
        self.show_deny_modal = True

    def _submit_denial_with_reason(self, reason_code: str) -> None:
        if not self.session or self.session.finished:
            return
        self.show_deny_modal = False
        self.app.audio.play("stamp")
        self.particles.spawn_stamp_sparks(580, 320, "DENIED", False)
        outcome = self.session.submit_decision(DECISION_DENY, reason_code=reason_code)
        self._after_decision(outcome)

    def _on_request_doc_clicked(self) -> None:
        if not self.session or self.session.finished:
            return
        self.app.audio.play("stamp")
        self.particles.spawn_stamp_sparks(580, 320, "MISSING DOC", False)
        outcome = self.session.submit_decision(DECISION_REQUEST_DOC)
        self._after_decision(outcome)

    def _after_decision(self, outcome: ConsulDecisionOutcome) -> None:
        if outcome.correct:
            self.app.audio.play("coin")
        else:
            self.app.audio.play("error")

        self.feedback_banner = outcome
        self.feedback_timer = 3.2

        if self.session and self.session.finished:
            if self.session.won:
                self.app.audio.play("success")
                self.app.progress.record_consul_completion(
                    self.session.shift.id,
                    self.session.stars_earned,
                    self.session.earnings,
                )
            else:
                self.app.audio.play("error")
            self.app.show_consul_results(self.session)
        else:
            self._rebuild_applicant_cards()

    def _on_restart(self) -> None:
        if not self.session:
            return
        self.app.audio.play("page")
        self.session.restart()
        self.paused = False
        self.show_deny_modal = False
        self.show_intro_modal = False
        self.feedback_banner = None
        self._rebuild_applicant_cards()

    def _toggle_pause(self) -> None:
        self.app.audio.play("click")
        self.paused = not self.paused

    def _on_exit_to_select(self) -> None:
        self.app.audio.play("click")
        self.app.open_level_select("consul")

    def _on_exit_to_menu(self) -> None:
        self.app.audio.play("click")
        self.app.change_screen("menu")

    def handle_event(self, event: pygame.event.Event) -> None:
        """Process keyboard shortcuts, field discrepancy clicks, and stamp buttons."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.show_deny_modal:
                    self._close_deny_modal()
                elif self.show_intro_modal:
                    self._dismiss_intro()
                else:
                    self._toggle_pause()
                return
            if event.key == pygame.K_TAB and not self.paused and not self.show_intro_modal:
                self._toggle_rulebook()
                return
            if event.key == pygame.K_r and not self.paused:
                self._on_restart()
                return

        if self.paused:
            for b in self.pause_buttons:
                b.handle_event(event)
            return

        if self.show_intro_modal:
            self.intro_start_btn.handle_event(event)
            return

        if self.show_deny_modal:
            self.cancel_deny_btn.handle_event(event)
            for b, _ in self.reason_buttons:
                b.handle_event(event)
            return

        for b in self.top_buttons:
            b.handle_event(event)
        for b in self.stamp_buttons:
            b.handle_event(event)

        # Clicking on a document field toggles discrepancy flag
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.session:
            for card in self.doc_cards:
                hovered = card.get_hovered_field(event.pos)
                if hovered is not None:
                    fname, _ = hovered
                    self.session.toggle_flag_field(card.doc.doc_type, fname)
                    self.app.audio.play("click")
                    break

    def update(self, dt: float) -> None:
        """Update shift countdown timer, slide-out rulebook animation, and particles."""
        self.particles.update(dt)

        # Smooth easing for Rulebook panel slide in/out
        target_rb = 1.0 if self.rulebook_open else 0.0
        self.rulebook_anim += (target_rb - self.rulebook_anim) * min(1.0, dt * 10.0)

        if self.feedback_timer > 0.0:
            self.feedback_timer = max(0.0, self.feedback_timer - dt)
            if self.feedback_timer == 0.0:
                self.feedback_banner = None

        if self.paused:
            for b in self.pause_buttons:
                b.update(dt)
            return
        if self.show_intro_modal:
            self.intro_start_btn.update(dt)
            return
        if self.show_deny_modal:
            self.cancel_deny_btn.update(dt)
            for b, _ in self.reason_buttons:
                b.update(dt)
            return

        if self.session:
            time_expired = self.session.update_timer(dt)
            if time_expired:
                if self.session.won:
                    self.app.progress.record_consul_completion(
                        self.session.shift.id,
                        self.session.stars_earned,
                        self.session.earnings,
                    )
                self.app.show_consul_results(self.session)
                return

        for b in self.top_buttons:
            b.update(dt)
        for b in self.stamp_buttons:
            b.update(dt)

    def draw(self, surface: pygame.Surface) -> None:
        """Render the Consular Booth: applicant window, inspection desk with paper cards, stamps, and rulebook."""
        surface.fill(COLOR_BG_MAIN)
        if not self.session:
            return

        sh = self.session.shift
        app_case = self.session.current_applicant
        dest_spec = self.app.db.countries[sh.destination]

        # 1. Top status bar
        pygame.draw.rect(surface, COLOR_BG_DARK, pygame.Rect(0, 0, SCREEN_WIDTH, 58))
        pygame.draw.line(surface, COLOR_BORDER, (0, 58), (SCREEN_WIDTH, 58), 2)

        f_hdr = self.app.fonts.get(19, bold=True)
        f_stat = self.app.fonts.get(16, bold=True)
        f_small = self.app.fonts.get(13)
        f_bold = self.app.fonts.get(14, bold=True)

        title_s = f_hdr.render(f"{sh.title} ({dest_spec.name} Desk)", True, COLOR_ACCENT_GOLD)
        surface.blit(title_s, (20, 17))

        # Day & Queue counter
        q_box = pygame.Rect(340, 10, 210, 38)
        pygame.draw.rect(surface, COLOR_BG_PANEL, q_box, border_radius=6)
        q_num = min(self.session.current_index + 1, len(self.session.queue))
        q_s = f_stat.render(f"Day {sh.current_day}  •  Applicant {q_num}/{len(self.session.queue)}", True, COLOR_TEXT_MAIN)
        surface.blit(q_s, (q_box.centerx - q_s.get_width() // 2, q_box.centery - q_s.get_height() // 2))

        # Strikes counter
        st_box = pygame.Rect(560, 10, 160, 38)
        pygame.draw.rect(surface, COLOR_BG_PANEL, st_box, border_radius=6)
        st_col = COLOR_DANGER if self.session.strikes > 0 else COLOR_TEXT_MUTED
        st_s = f_stat.render(f"STRIKES: {self.session.strikes}/{sh.max_strikes}", True, st_col)
        surface.blit(st_s, (st_box.centerx - st_s.get_width() // 2, st_box.centery - st_s.get_height() // 2))

        # Pay / Timer counter
        pay_box = pygame.Rect(730, 10, 170, 38)
        pygame.draw.rect(surface, COLOR_BG_PANEL, pay_box, border_radius=6)
        if sh.time_limit_seconds > 0:
            t_left = int(self.session.time_remaining)
            pay_txt = f"Pay: ${self.session.earnings} • {t_left}s"
        else:
            pay_txt = f"SALARY: ${self.session.earnings}"
        pay_s = f_stat.render(pay_txt, True, COLOR_SUCCESS)
        surface.blit(pay_s, (pay_box.centerx - pay_s.get_width() // 2, pay_box.centery - pay_s.get_height() // 2))

        for b in self.top_buttons:
            b.draw(surface, self.app.fonts)

        # 2. Left Panel: Applicant Booth & Interview Window
        booth_panel = Panel(pygame.Rect(16, 68, 290, SCREEN_HEIGHT - 84), title="APPLICANT BOOTH")
        booth_panel.draw(surface, self.app.fonts)

        if app_case:
            port_rect = pygame.Rect(86, 114, 150, 170)
            draw_portrait(surface, port_rect, app_case.portrait)

            # Name & Nationality
            origin_country = self.app.db.countries[app_case.origin]
            flag_r = pygame.Rect(34, 298, 36, 24)
            draw_flag(surface, flag_r, origin_country.flag)

            n_surf = f_hdr.render(app_case.name, True, COLOR_TEXT_MAIN)
            surface.blit(n_surf, (78, 296))

            nat_s = f_bold.render(f"Citizen of {origin_country.name}", True, COLOR_ACCENT_GOLD)
            surface.blit(nat_s, (34, 330))

            route_str = f"Origin: {origin_country.name} → {dest_spec.name}"
            if app_case.transit_countries:
                t_names = [self.app.db.countries[c].name for c in app_case.transit_countries]
                route_str = f"Via Transit: {', '.join(t_names)}"
                r_col = COLOR_ACCENT_ORANGE
            else:
                r_col = COLOR_TEXT_MUTED
            r_surf = f_bold.render(route_str, True, r_col)
            surface.blit(r_surf, (34, 354))

            # Speech bubble
            bubble_rect = pygame.Rect(30, 386, 262, 108)
            pygame.draw.rect(surface, COLOR_BG_DARK, bubble_rect, border_radius=8)
            pygame.draw.rect(surface, COLOR_BORDER, bubble_rect, width=1, border_radius=8)
            draw_text_wrapped(
                surface,
                f"\"{app_case.dialogue}\"",
                f_small,
                COLOR_TEXT_MAIN,
                bubble_rect.inflate(-18, -16),
                line_spacing=4,
            )

            # Notice board / directive announcement if present
            if sh.announcement:
                notice_rect = pygame.Rect(30, 506, 262, 180)
                pygame.draw.rect(surface, (52, 42, 34), notice_rect, border_radius=8)
                pygame.draw.rect(surface, COLOR_ACCENT_GOLD, notice_rect, width=2, border_radius=8)
                n_hdr = f_bold.render("MINISTRY NOTICE BOARD", True, COLOR_ACCENT_GOLD)
                surface.blit(n_hdr, (notice_rect.x + 12, notice_rect.y + 8))
                draw_text_wrapped(
                    surface,
                    sh.announcement,
                    f_small,
                    COLOR_TEXT_MAIN,
                    pygame.Rect(notice_rect.x + 12, notice_rect.y + 32, notice_rect.width - 24, 140),
                    line_spacing=3,
                )
            else:
                tip_rect = pygame.Rect(30, 514, 262, 165)
                pygame.draw.rect(surface, COLOR_BG_DARK, tip_rect, border_radius=8)
                draw_text_wrapped(
                    surface,
                    "INSPECTION TIP:\nClick any suspicious field on the paper cards (name, expiry, country, balance, or missing stamp) to highlight discrepancies in red before stamping!",
                    f_small,
                    COLOR_TEXT_MUTED,
                    tip_rect.inflate(-20, -20),
                    line_spacing=4,
                )

        # 3. Center Panel: Top-Down Consular Inspection Desk
        desk_rect = pygame.Rect(314, 68, SCREEN_WIDTH - 330, SCREEN_HEIGHT - 152)
        pygame.draw.rect(surface, COLOR_DESK_WOOD, desk_rect, border_radius=10)
        mat_rect = desk_rect.inflate(-14, -14)
        pygame.draw.rect(surface, COLOR_DESK_MAT, mat_rect, border_radius=8)
        pygame.draw.rect(surface, COLOR_BORDER, desk_rect, width=2, border_radius=10)

        hovered_tip = ""
        mouse_pos = pygame.mouse.get_pos()

        for card in self.doc_cards:
            card.draw(
                surface,
                self.app.fonts,
                flagged_fields=self.session.flagged_fields,
                current_day=sh.current_day,
            )
            hf = card.get_hovered_field(mouse_pos)
            if hf is not None:
                hovered_tip = hf[1]

        # Feedback toast banner on top of desk if recent decision occurred
        if self.feedback_banner is not None:
            fb_rect = pygame.Rect(334, desk_rect.bottom - 74, 560, 62)
            fb_col = COLOR_SUCCESS_DARK if self.feedback_banner.correct else COLOR_DANGER_DARK
            pygame.draw.rect(surface, fb_col, fb_rect, border_radius=8)
            pygame.draw.rect(surface, COLOR_TEXT_MAIN, fb_rect, width=2, border_radius=8)
            t_fb = f_bold.render(self.feedback_banner.feedback_title, True, COLOR_TEXT_MAIN)
            surface.blit(t_fb, (fb_rect.x + 12, fb_rect.y + 8))
            if self.feedback_banner.feedback_details:
                d_fb = f_small.render(self.feedback_banner.feedback_details[0][:75], True, COLOR_TEXT_MAIN)
                surface.blit(d_fb, (fb_rect.x + 12, fb_rect.y + 32))

        # 4. Bottom Stamp Bar
        for b in self.stamp_buttons:
            b.draw(surface, self.app.fonts)
            if b.hovered and b.tooltip:
                hovered_tip = b.tooltip

        for b in self.top_buttons:
            if b.hovered and b.tooltip:
                hovered_tip = b.tooltip

        # 5. Slide-out Rulebook Panel on the right
        eased = ease_out_cubic(self.rulebook_anim)
        rb_w = 340
        rb_x = SCREEN_WIDTH - int((rb_w + 14) * eased)
        if rb_x < SCREEN_WIDTH:
            rb_rect = pygame.Rect(rb_x, 76, rb_w, 456)
            rb_panel = Panel(rb_rect, title=f"CONSULAR RULEBOOK — {dest_spec.name.upper()}")
            rb_panel.draw(surface, self.app.fonts)

            y_cursor = rb_rect.y + 46
            for idx, rule_line in enumerate(sh.active_rules_summary):
                y_cursor = draw_text_wrapped(
                    surface,
                    f"{idx + 1}. {rule_line}",
                    f_small,
                    COLOR_TEXT_MAIN,
                    pygame.Rect(rb_rect.x + 14, y_cursor, rb_rect.width - 28, 65),
                    line_spacing=3,
                )
                y_cursor += 8

            # Quick reference table of relations
            pygame.draw.line(
                surface,
                COLOR_BORDER,
                (rb_rect.x + 14, y_cursor + 4),
                (rb_rect.right - 14, y_cursor + 4),
                1,
            )
            y_cursor += 12
            rel_hdr = f_bold.render(f"{dest_spec.name} Diplomatic Visa Table:", True, COLOR_ACCENT_GOLD)
            surface.blit(rel_hdr, (rb_rect.x + 14, y_cursor))
            y_cursor += 24

            for cid, cspec in self.app.db.countries.items():
                if cid == dest_spec.id:
                    continue
                vf = dest_spec.is_visa_free_for(cid)
                status_str = "VISA-FREE" if vf else "VISA REQUIRED"
                s_col = COLOR_SUCCESS if vf else COLOR_ACCENT_ORANGE
                c_line = f_small.render(f"• {cspec.name}:", True, COLOR_TEXT_MAIN)
                st_line = f_bold.render(status_str, True, s_col)
                surface.blit(c_line, (rb_rect.x + 18, y_cursor))
                surface.blit(st_line, (rb_rect.x + 145, y_cursor))
                y_cursor += 20

        self.particles.draw(surface, self.app.fonts.get(18, bold=True))

        # Modals
        if self.show_intro_modal:
            self._draw_intro_modal(surface)
        elif self.show_deny_modal:
            self._draw_deny_modal(surface)
        elif self.paused:
            self._draw_pause_modal(surface)
        elif hovered_tip:
            self.tooltip.draw(surface, hovered_tip, mouse_pos, self.app.fonts)

    def _draw_intro_modal(self, surface: pygame.Surface) -> None:
        if not self.session:
            return
        sh = self.session.shift
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((10, 14, 22, 195))
        surface.blit(overlay, (0, 0))

        box = pygame.Rect(SCREEN_WIDTH // 2 - 340, 110, 680, 480)
        modal = Panel(box, title=f"CONSULAR SHIFT BRIEFING — {sh.title.upper()}")
        modal.draw(surface, self.app.fonts)

        f_sub = self.app.fonts.get(18, bold=True)
        f_body = self.app.fonts.get(15)
        f_bold = self.app.fonts.get(15, bold=True)

        sub_s = f_sub.render(sh.subtitle, True, COLOR_ACCENT_GOLD)
        surface.blit(sub_s, (box.x + 28, box.y + 52))

        draw_text_wrapped(
            surface,
            sh.intro_text,
            f_body,
            COLOR_TEXT_MAIN,
            pygame.Rect(box.x + 28, box.y + 88, box.width - 56, 130),
            line_spacing=5,
        )

        rules_box = pygame.Rect(box.x + 28, box.y + 225, box.width - 56, 170)
        pygame.draw.rect(surface, COLOR_BG_DARK, rules_box, border_radius=8)
        pygame.draw.rect(surface, COLOR_ACCENT_TEAL, rules_box, width=1, border_radius=8)

        r_hdr = f_bold.render("SHIFT STANDING ORDERS:", True, COLOR_ACCENT_TEAL)
        surface.blit(r_hdr, (rules_box.x + 14, rules_box.y + 10))
        ry = rules_box.y + 36
        for line in sh.active_rules_summary:
            ry = draw_text_wrapped(
                surface,
                f"• {line}",
                f_body,
                COLOR_TEXT_MAIN,
                pygame.Rect(rules_box.x + 14, ry, rules_box.width - 28, 44),
            )
            ry += 4

        self.intro_start_btn.draw(surface, self.app.fonts)

    def _draw_deny_modal(self, surface: pygame.Surface) -> None:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((10, 14, 22, 185))
        surface.blit(overlay, (0, 0))

        box = pygame.Rect(SCREEN_WIDTH // 2 - 250, 135, 500, 448)
        modal = Panel(box, title="SELECT OFFICIAL DENIAL REASON")
        modal.draw(surface, self.app.fonts)

        for b, _ in self.reason_buttons:
            b.draw(surface, self.app.fonts)
        self.cancel_deny_btn.draw(surface, self.app.fonts)

    def _draw_pause_modal(self, surface: pygame.Surface) -> None:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((10, 14, 22, 195))
        surface.blit(overlay, (0, 0))

        box = pygame.Rect(SCREEN_WIDTH // 2 - 200, 200, 400, 330)
        modal = Panel(box, title="SHIFT PAUSED")
        modal.draw(surface, self.app.fonts)
        for b in self.pause_buttons:
            b.draw(surface, self.app.fonts)
