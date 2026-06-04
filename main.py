#!/usr/bin/env python3
"""
Davi & Lucca Gol! — Jogo de futebol 2D
"""
import pygame
import sys
import math
import random
from constants import *
from player_data import PlayerData, load_players, add_player, delete_player
from constants import POSITIONS
from match import Match
from tournament import Tournament, TournamentTeam


# ── UI helpers ────────────────────────────────────────────────────────────────

class Button:
    def __init__(self, x, y, w, h, text,
                 col=BTN_COL, hover=BTN_HOVER, text_col=BTN_TEXT):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.col = col
        self.hover = hover
        self.text_col = text_col
        self._hov = False

    def update(self, mouse):
        self._hov = self.rect.collidepoint(mouse)

    def draw(self, surf, font):
        c = self.hover if self._hov else self.col
        pygame.draw.rect(surf, c, self.rect, border_radius=10)
        border_c = UI_ACCENT if self._hov else (90, 90, 160)
        pygame.draw.rect(surf, border_c, self.rect, 2, border_radius=10)
        ts = font.render(self.text, True, self.text_col)
        surf.blit(ts, ts.get_rect(center=self.rect.center))

    def clicked(self, ev):
        return ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and self._hov


class InputField:
    def __init__(self, x, y, w, h, placeholder="", kind="text"):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = ""
        self.placeholder = placeholder
        self.kind = kind   # "text" | "int" | "float"
        self.active = False
        self._blink = True
        self._bt = 0

    def handle(self, ev):
        if ev.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(ev.pos)
        if ev.type == pygame.KEYDOWN and self.active:
            if ev.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif ev.key == pygame.K_RETURN:
                self.active = False
            elif ev.unicode.isprintable():
                if self.kind == "int" and ev.unicode.isdigit():
                    self.text += ev.unicode
                elif self.kind == "float" and (ev.unicode.isdigit() or
                        (ev.unicode == '.' and '.' not in self.text)):
                    self.text += ev.unicode
                elif self.kind == "text" and len(self.text) < 28:
                    self.text += ev.unicode

    def tick(self):
        self._bt += 1
        if self._bt >= 28:
            self._bt = 0
            self._blink = not self._blink

    def as_int(self, default=0):
        try: return int(self.text)
        except: return default

    def as_float(self, default=0.0):
        try: return float(self.text)
        except: return default

    def draw(self, surf, font):
        bg = (40, 40, 85) if self.active else (28, 28, 60)
        border = UI_ACCENT if self.active else (90, 90, 140)
        pygame.draw.rect(surf, bg, self.rect, border_radius=6)
        pygame.draw.rect(surf, border, self.rect, 2, border_radius=6)
        disp = self.text or self.placeholder
        tc = WHITE if self.text else GRAY
        ts = font.render(disp, True, tc)
        surf.blit(ts, (self.rect.x + 8,
                       self.rect.centery - ts.get_height() // 2))
        if self.active and self._blink:
            cx = self.rect.x + 8 + (font.size(self.text)[0] if self.text else 0) + 2
            pygame.draw.line(surf, WHITE,
                             (cx, self.rect.y + 6),
                             (cx, self.rect.bottom - 6), 2)


class SelectField:
    """Cycle through a list of options."""
    def __init__(self, x, y, w, h, options, label=""):
        self.rect = pygame.Rect(x, y, w, h)
        self.options = options
        self.label = label
        self.idx = 0
        bw = 36
        self.btn_left  = pygame.Rect(x, y, bw, h)
        self.btn_right = pygame.Rect(x + w - bw, y, bw, h)

    @property
    def value(self):
        return self.options[self.idx]

    def handle(self, ev):
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if self.btn_left.collidepoint(ev.pos):
                self.idx = (self.idx - 1) % len(self.options)
            elif self.btn_right.collidepoint(ev.pos):
                self.idx = (self.idx + 1) % len(self.options)

    def draw(self, surf, font):
        pygame.draw.rect(surf, (28, 28, 60), self.rect, border_radius=6)
        pygame.draw.rect(surf, (90, 90, 140), self.rect, 2, border_radius=6)
        for btn, txt in [(self.btn_left, "<"), (self.btn_right, ">")]:
            pygame.draw.rect(surf, BTN_COL, btn, border_radius=6)
            ts = font.render(txt, True, WHITE)
            surf.blit(ts, ts.get_rect(center=btn.center))
        val_s = font.render(str(self.value), True, WHITE)
        surf.blit(val_s, val_s.get_rect(center=self.rect.center))


# ── Main application ──────────────────────────────────────────────────────────

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("Davi & Lucca Gol!")
        self.clock = pygame.time.Clock()

        self.fnt_title = pygame.font.SysFont("arial", 62, bold=True)
        self.fnt_big   = pygame.font.SysFont("arial", 46, bold=True)
        self.fnt_mid   = pygame.font.SysFont("arial", 32, bold=True)
        self.fnt_sm    = pygame.font.SysFont("arial", 22)
        self.fnt_xs    = pygame.font.SysFont("arial", 16)

        self.screen_stack = ["main"]
        self.running = True

        # Shared state between menus
        self.tour: Tournament | None = None

        # Stars background
        self.stars = [(random.randint(0, SCREEN_W), random.randint(0, SCREEN_H),
                       random.randint(1, 3)) for _ in range(80)]

    # ── Navigation ────────────────────────────────────────────────────────────

    def push(self, name):
        self.screen_stack.append(name)

    def pop(self):
        if len(self.screen_stack) > 1:
            self.screen_stack.pop()

    # ── Drawing helpers ───────────────────────────────────────────────────────

    def bg(self):
        self.screen.fill(DARK_BG)
        for sx, sy, sr in self.stars:
            pygame.draw.circle(self.screen, (180, 180, 220), (sx, sy), sr)

    def panel(self, rect, alpha=210):
        s = pygame.Surface(rect.size, pygame.SRCALPHA)
        s.fill((20, 20, 58, alpha))
        self.screen.blit(s, rect.topleft)
        pygame.draw.rect(self.screen, (80, 80, 155), rect, 2, border_radius=14)

    def title(self, text, y=45, color=UI_ACCENT):
        sh = self.fnt_title.render(text, True, BLACK)
        ts = self.fnt_title.render(text, True, color)
        r = ts.get_rect(center=(SCREEN_W // 2, y))
        self.screen.blit(sh, (r.x + 3, r.y + 3))
        self.screen.blit(ts, r)

    def label(self, text, x, y, color=LIGHT_GRAY, font=None):
        f = font or self.fnt_sm
        s = f.render(text, True, color)
        self.screen.blit(s, (x, y))
        return s.get_width()

    def centered(self, text, y, color=WHITE, font=None):
        f = font or self.fnt_sm
        s = f.render(text, True, color)
        self.screen.blit(s, s.get_rect(center=(SCREEN_W // 2, y)))

    def events_and_mouse(self):
        evs = pygame.event.get()
        for ev in evs:
            if ev.type == pygame.QUIT:
                pygame.quit(); sys.exit()
        return evs, pygame.mouse.get_pos(), pygame.key.get_pressed()

    # ── Screens ───────────────────────────────────────────────────────────────

    def screen_main(self):
        cx = SCREEN_W // 2
        bw, bh = 310, 58
        bx = cx - bw // 2
        buttons = [
            Button(bx, 190, bw, bh, "⚽  Jogar Partida"),
            Button(bx, 265, bw, bh, "🏆  Torneio"),
            Button(bx, 340, bw, bh, "👤  Criar Jogador"),
            Button(bx, 415, bw, bh, "📋  Ver Jogadores"),
            Button(bx, 510, bw, bh, "❌  Sair",
                   BTN_DANGER, BTN_DANGER_H),
        ]

        evs, mouse, _ = self.events_and_mouse()
        for ev in evs:
            if buttons[0].clicked(ev): self.push("select_match")
            if buttons[1].clicked(ev): self.push("tournament_setup")
            if buttons[2].clicked(ev): self.push("create_player")
            if buttons[3].clicked(ev): self.push("player_list")
            if buttons[4].clicked(ev): self.running = False

        self.bg()
        self.title("⚽  DAVI & LUCCA  GOL!  ⚽")
        self.centered("O melhor jogo de futebol dos irmãos", 108, GRAY, self.fnt_sm)

        for b in buttons:
            b.update(mouse)
            b.draw(self.screen, self.fnt_mid)

        # Decorative balls
        t = pygame.time.get_ticks() / 1000
        for i, (ox, oy, amp, spd) in enumerate(
                [(120, 380, 30, 0.8), (SCREEN_W - 130, 320, 25, 1.1)]):
            y = oy + int(math.sin(t * spd + i) * amp)
            pygame.draw.circle(self.screen, WHITE, (ox, y), 22, 3)
            pygame.draw.circle(self.screen, GRAY, (ox, y), 22 // 2, 2)

    # ─────────────────────────────────────────────────────────────────────────
    # Select match
    # ─────────────────────────────────────────────────────────────────────────

    def screen_select_match(self):
        cx = SCREEN_W // 2

        if not hasattr(self, '_sm_init'):
            self._sm_init = True
            players = load_players()
            pnames = [p.name for p in players] + ["--- IA ---"]
            self._sm_mode   = SelectField(cx - 120, 200, 240, 48,
                                          ["1 contra 1", "2 contra 2"], "Modo")
            self._sm_diff   = SelectField(cx - 120, 275, 240, 48,
                                          ["facil", "normal", "dificil"], "Dificuldade IA")
            self._sm_diff.idx = 1
            self._sm_ctrl   = SelectField(cx - 120, 350, 240, 48,
                                          ["Ambos (2 humanos)", "Só Time A", "Só Time B",
                                           "Só IA"], "Controle")
            self._sm_players = players
            pnames_full = ["(nenhum)"] + [f"#{p.jersey_number} {p.name}" for p in players]
            self._sm_pa1 = SelectField(cx - 230, 460, 200, 44, pnames_full, "A1")
            self._sm_pb1 = SelectField(cx + 30,  460, 200, 44, pnames_full, "B1")
            self._sm_pa2 = SelectField(cx - 230, 520, 200, 44, pnames_full, "A2")
            self._sm_pb2 = SelectField(cx + 30,  520, 200, 44, pnames_full, "B2")

            self._sm_btn_play = Button(cx - 130, 600, 260, 55, "▶  JOGAR")
            self._sm_btn_back = Button(cx - 130, 660, 260, 46, "← Voltar",
                                       BTN_DANGER, BTN_DANGER_H)

        evs, mouse, _ = self.events_and_mouse()
        for ev in evs:
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                del self._sm_init; self.pop(); return

            self._sm_mode.handle(ev)
            self._sm_diff.handle(ev)
            self._sm_ctrl.handle(ev)
            self._sm_pa1.handle(ev)
            self._sm_pb1.handle(ev)
            self._sm_pa2.handle(ev)
            self._sm_pb2.handle(ev)

            if self._sm_btn_play.clicked(ev):
                self._launch_quick_match()
            if self._sm_btn_back.clicked(ev):
                del self._sm_init; self.pop(); return

        is_2v2 = "2" in self._sm_mode.value

        self.bg()
        self.title("Configurar Partida", 45)
        self.panel(pygame.Rect(cx - 280, 170, 560, 500))

        self.centered("Modo de Jogo", 178, LIGHT_GRAY, self.fnt_xs)
        self._sm_mode.draw(self.screen, self.fnt_sm)
        self.centered("Dificuldade da IA", 253, LIGHT_GRAY, self.fnt_xs)
        self._sm_diff.draw(self.screen, self.fnt_sm)
        self.centered("Quem controla", 328, LIGHT_GRAY, self.fnt_xs)
        self._sm_ctrl.draw(self.screen, self.fnt_sm)

        if self._sm_players:
            self.centered("Jogadores salvos (opcional)", 438, LIGHT_GRAY, self.fnt_xs)
            self.label("Time A", cx - 220, 448, RED, self.fnt_xs)
            self.label("Time B", cx + 40, 448, BLUE, self.fnt_xs)
            self._sm_pa1.draw(self.screen, self.fnt_xs)
            self._sm_pb1.draw(self.screen, self.fnt_xs)
            if is_2v2:
                self._sm_pa2.draw(self.screen, self.fnt_xs)
                self._sm_pb2.draw(self.screen, self.fnt_xs)

        self._sm_btn_play.update(mouse)
        self._sm_btn_play.draw(self.screen, self.fnt_mid)
        self._sm_btn_back.update(mouse)
        self._sm_btn_back.draw(self.screen, self.fnt_sm)

    def _get_player_data_from_select(self, sel):
        v = sel.value
        if v == "(nenhum)":
            return None
        idx = sel.idx - 1
        if 0 <= idx < len(self._sm_players):
            return self._sm_players[idx]
        return None

    def _launch_quick_match(self):
        mode_str = "1v1" if "1" in self._sm_mode.value else "2v2"
        ctrl_map = {
            "Ambos (2 humanos)": "both",
            "Só Time A": "a",
            "Só Time B": "b",
            "Só IA": "none",
        }
        human_ctrl = ctrl_map.get(self._sm_ctrl.value, "both")
        diff = self._sm_diff.value

        pa1 = self._get_player_data_from_select(self._sm_pa1)
        pb1 = self._get_player_data_from_select(self._sm_pb1)
        pa2 = self._get_player_data_from_select(self._sm_pa2)
        pb2 = self._get_player_data_from_select(self._sm_pb2)

        team_a_data = [p for p in [pa1, pa2] if p] or None
        team_b_data = [p for p in [pb1, pb2] if p] or None

        m = Match(self.screen, self.clock,
                  mode=mode_str,
                  team_a_data=team_a_data,
                  team_b_data=team_b_data,
                  human_control=human_ctrl,
                  ai_diff=diff,
                  team_a_name="Time A",
                  team_b_name="Time B",
                  team_a_color=RED,
                  team_b_color=BLUE)
        result = m.run()
        if result == 'menu':
            del self._sm_init; self.pop()

    # ─────────────────────────────────────────────────────────────────────────
    # Create player
    # ─────────────────────────────────────────────────────────────────────────

    def screen_create_player(self):
        cx = SCREEN_W // 2

        if not hasattr(self, '_cp_init'):
            self._cp_init = True
            fw = 340
            fx = cx - fw // 2
            self._cp_name   = InputField(fx, 195, fw, 46, "Nome do jogador")
            self._cp_age    = InputField(fx, 270, fw // 2 - 5, 46, "Idade", "int")
            self._cp_num    = InputField(fx + fw // 2 + 5, 270, fw // 2 - 5, 46,
                                         "Nº camisa", "int")
            self._cp_height = InputField(fx, 340, fw // 2 - 5, 46, "Altura cm", "float")
            self._cp_pos    = SelectField(fx + fw // 2 + 5, 340, fw // 2 - 5, 46,
                                          POSITIONS)
            self._cp_team   = SelectField(fx, 415, fw, 46,
                                          list(TEAM_COLOR_OPTIONS.keys()))
            self._cp_msg    = ""
            self._cp_msg_t  = 0
            self._cp_btn_save = Button(cx - 150, 490, 300, 55, "💾  Salvar Jogador")
            self._cp_btn_back = Button(cx - 100, 558, 200, 44, "← Voltar",
                                       BTN_DANGER, BTN_DANGER_H)

        evs, mouse, _ = self.events_and_mouse()
        for ev in evs:
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                del self._cp_init; self.pop(); return

            self._cp_name.handle(ev)
            self._cp_age.handle(ev)
            self._cp_num.handle(ev)
            self._cp_height.handle(ev)
            self._cp_pos.handle(ev)
            self._cp_team.handle(ev)

            if self._cp_btn_save.clicked(ev):
                self._save_player()
            if self._cp_btn_back.clicked(ev):
                del self._cp_init; self.pop(); return

        for f in [self._cp_name, self._cp_age, self._cp_num, self._cp_height]:
            f.tick()

        if self._cp_msg_t > 0:
            self._cp_msg_t -= 1

        self.bg()
        self.title("Criar Jogador", 45)
        self.panel(pygame.Rect(cx - 220, 165, 440, 400))

        def lbl(t, x, y): self.label(t, x, y, LIGHT_GRAY, self.fnt_xs)
        lbl("Nome",        cx - 170, 180)
        self._cp_name.draw(self.screen, self.fnt_sm)

        lbl("Idade", cx - 170, 255)
        self._cp_age.draw(self.screen, self.fnt_sm)
        lbl("Nº camisa", cx + 10, 255)
        self._cp_num.draw(self.screen, self.fnt_sm)

        lbl("Altura (cm)", cx - 170, 325)
        self._cp_height.draw(self.screen, self.fnt_sm)
        lbl("Posição", cx + 10, 325)
        self._cp_pos.draw(self.screen, self.fnt_sm)

        lbl("Cor do time",  cx - 170, 400)
        self._cp_team.draw(self.screen, self.fnt_sm)

        # Preview color swatch
        tc = TEAM_COLOR_OPTIONS.get(self._cp_team.value, RED)
        pygame.draw.rect(self.screen, tc,
                         (cx - 170, 465, 24, 24), border_radius=4)

        self._cp_btn_save.update(mouse)
        self._cp_btn_save.draw(self.screen, self.fnt_mid)
        self._cp_btn_back.update(mouse)
        self._cp_btn_back.draw(self.screen, self.fnt_sm)

        if self._cp_msg_t > 0:
            col = GREEN_COL if "salvo" in self._cp_msg else RED
            self.centered(self._cp_msg, 618, col, self.fnt_sm)

    def _save_player(self):
        name = self._cp_name.text.strip()
        if not name:
            self._cp_msg = "Digite um nome!"
            self._cp_msg_t = 90; return
        age = self._cp_age.as_int()
        num = self._cp_num.as_int()
        ht  = self._cp_height.as_float()
        if age <= 0: age = 17
        if num <= 0: num = 10
        if ht  <= 0: ht  = 175.0

        pd = PlayerData(name=name, age=age, position=self._cp_pos.value,
                        height=ht, team=self._cp_team.value, jersey_number=num)
        add_player(pd)
        self._cp_msg = f"Jogador '{name}' salvo com sucesso!"
        self._cp_msg_t = 120
        self._cp_name.text = ""
        self._cp_age.text  = ""
        self._cp_num.text  = ""
        self._cp_height.text = ""

    # ─────────────────────────────────────────────────────────────────────────
    # Player list
    # ─────────────────────────────────────────────────────────────────────────

    def screen_player_list(self):
        cx = SCREEN_W // 2

        if not hasattr(self, '_pl_init'):
            self._pl_init = True
            self._pl_scroll = 0
            self._pl_msg = ""
            self._pl_msg_t = 0
            self._pl_btn_back = Button(cx - 100, 650, 200, 46, "← Voltar",
                                       BTN_DANGER, BTN_DANGER_H)

        players = load_players()
        evs, mouse, _ = self.events_and_mouse()

        for ev in evs:
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                del self._pl_init; self.pop(); return
            if ev.type == pygame.MOUSEWHEEL:
                self._pl_scroll = max(0, self._pl_scroll - ev.y)
            if self._pl_btn_back.clicked(ev):
                del self._pl_init; self.pop(); return

        if self._pl_msg_t > 0:
            self._pl_msg_t -= 1

        self.bg()
        self.title("Jogadores Cadastrados", 45)

        if not players:
            self.centered("Nenhum jogador cadastrado ainda.", SCREEN_H // 2, GRAY, self.fnt_sm)
            self.centered("Crie jogadores no menu principal.", SCREEN_H // 2 + 35, GRAY, self.fnt_xs)
        else:
            panel_rect = pygame.Rect(cx - 380, 90, 760, 545)
            self.panel(panel_rect)

            row_h = 62
            vis   = 8
            max_scroll = max(0, len(players) - vis)
            self._pl_scroll = min(self._pl_scroll, max_scroll)

            header = ["#",  "Nome",       "Pos",          "Idade", "Alt.", "Time"]
            hx     = [50,   120,          340,            440,     505,    570]
            for htext, hxpos in zip(header, hx):
                hs = self.fnt_xs.render(htext, True, UI_ACCENT)
                self.screen.blit(hs, (cx - 370 + hxpos, 98))

            pygame.draw.line(self.screen, (80, 80, 150),
                             (cx - 370, 114), (cx + 375, 114), 1)

            clip = pygame.Rect(cx - 380, 115, 760, vis * row_h)
            self.screen.set_clip(clip)

            for i, p in enumerate(players[self._pl_scroll:self._pl_scroll + vis]):
                real_i = i + self._pl_scroll
                ry = 122 + i * row_h

                if i % 2 == 0:
                    row_s = pygame.Surface((756, row_h - 4), pygame.SRCALPHA)
                    row_s.fill((255, 255, 255, 10))
                    self.screen.blit(row_s, (cx - 378, ry - 2))

                col = TEAM_COLOR_OPTIONS.get(p.team, WHITE)
                vals = [str(p.jersey_number), p.name, p.position,
                        str(p.age), f"{p.height}cm", p.team]
                for v, hxpos in zip(vals, hx):
                    vc = col if v == p.team else LIGHT_GRAY
                    vs = self.fnt_xs.render(v, True, vc)
                    self.screen.blit(vs, (cx - 370 + hxpos, ry + row_h // 2 - vs.get_height() // 2))

                # Delete button
                del_btn = pygame.Rect(cx + 300, ry + 8, 66, 28)
                del_hov = del_btn.collidepoint(mouse)
                pygame.draw.rect(self.screen, BTN_DANGER_H if del_hov else BTN_DANGER,
                                 del_btn, border_radius=6)
                ds = self.fnt_xs.render("Apagar", True, WHITE)
                self.screen.blit(ds, ds.get_rect(center=del_btn.center))

                for ev in evs:
                    if (ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1
                            and del_btn.collidepoint(ev.pos)):
                        delete_player(real_i)
                        self._pl_msg = f"'{p.name}' removido."
                        self._pl_msg_t = 90
                        break

            self.screen.set_clip(None)

        if self._pl_msg_t > 0:
            self.centered(self._pl_msg, 632, YELLOW, self.fnt_sm)

        self._pl_btn_back.update(mouse)
        self._pl_btn_back.draw(self.screen, self.fnt_sm)

        total = len(players)
        self.centered(f"Total: {total} jogador(es)", 700, GRAY, self.fnt_xs)

    # ─────────────────────────────────────────────────────────────────────────
    # Tournament setup
    # ─────────────────────────────────────────────────────────────────────────

    def screen_tournament_setup(self):
        cx = SCREEN_W // 2

        if not hasattr(self, '_ts_init'):
            self._ts_init = True
            self._ts_name  = InputField(cx - 160, 240, 320, 50, "Nome do seu time")
            self._ts_col   = SelectField(cx - 160, 310, 320, 50,
                                         list(TEAM_COLOR_OPTIONS.keys()))
            players = load_players()
            pnames = ["(nenhum)"] + [f"#{p.jersey_number} {p.name}" for p in players]
            self._ts_p1 = SelectField(cx - 200, 390, 200, 46, pnames)
            self._ts_p2 = SelectField(cx - 200, 448, 200, 46, pnames)
            self._ts_mode  = SelectField(cx - 100, 515, 200, 46,
                                         ["1v1", "2v2"])
            self._ts_players = players
            self._ts_btn_go   = Button(cx - 140, 590, 280, 55, "🏆  Iniciar Torneio")
            self._ts_btn_back = Button(cx - 100, 655, 200, 46, "← Voltar",
                                       BTN_DANGER, BTN_DANGER_H)

        evs, mouse, _ = self.events_and_mouse()
        for ev in evs:
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                del self._ts_init; self.pop(); return
            self._ts_name.handle(ev)
            self._ts_col.handle(ev)
            self._ts_p1.handle(ev)
            self._ts_p2.handle(ev)
            self._ts_mode.handle(ev)

            if self._ts_btn_go.clicked(ev):
                self._start_tournament()
                if self.tour:
                    del self._ts_init
                    self.push("tournament")
                return
            if self._ts_btn_back.clicked(ev):
                del self._ts_init; self.pop(); return

        self._ts_name.tick()

        self.bg()
        self.title("Configurar Torneio", 45)
        self.panel(pygame.Rect(cx - 240, 200, 480, 465))

        def lbl(t, x, y): self.label(t, x, y, LIGHT_GRAY, self.fnt_xs)
        lbl("Nome do seu time", cx - 155, 225)
        self._ts_name.draw(self.screen, self.fnt_sm)
        lbl("Cor do time", cx - 155, 295)
        self._ts_col.draw(self.screen, self.fnt_sm)

        tc = TEAM_COLOR_OPTIONS.get(self._ts_col.value, RED)
        pygame.draw.rect(self.screen, tc, (cx + 165, 316, 20, 20), border_radius=4)

        lbl("Jogador 1 (opcional)", cx - 195, 375)
        self._ts_p1.draw(self.screen, self.fnt_xs)
        lbl("Jogador 2 (2v2)", cx - 195, 433)
        self._ts_p2.draw(self.screen, self.fnt_xs)
        lbl("Modo", cx - 95, 500)
        self._ts_mode.draw(self.screen, self.fnt_sm)

        self._ts_btn_go.update(mouse)
        self._ts_btn_go.draw(self.screen, self.fnt_mid)
        self._ts_btn_back.update(mouse)
        self._ts_btn_back.draw(self.screen, self.fnt_sm)

        self.centered("8 times • Eliminação simples", 720, GRAY, self.fnt_xs)

    def _get_player_ts(self, sel):
        v = sel.value
        if v == "(nenhum)": return None
        idx = sel.idx - 1
        if 0 <= idx < len(self._ts_players):
            return self._ts_players[idx]
        return None

    def _start_tournament(self):
        name = self._ts_name.text.strip() or "Meu Time"
        col  = TEAM_COLOR_OPTIONS.get(self._ts_col.value, RED)
        p1   = self._get_player_ts(self._ts_p1)
        p2   = self._get_player_ts(self._ts_p2)
        players = [p for p in [p1, p2] if p]
        self.tour = Tournament(name, players, col)
        self._tour_mode = self._ts_mode.value

    # ─────────────────────────────────────────────────────────────────────────
    # Tournament bracket / runner
    # ─────────────────────────────────────────────────────────────────────────

    def screen_tournament(self):
        if not self.tour:
            self.pop(); return

        t = self.tour
        cx = SCREEN_W // 2

        if t.is_done():
            self._draw_champion_screen(t)
            evs, mouse, _ = self.events_and_mouse()
            btn_back = Button(cx - 120, 600, 240, 52, "🏠  Menu Principal",
                              BTN_DANGER, BTN_DANGER_H)
            btn_back.update(mouse)
            btn_back.draw(self.screen, self.fnt_sm)
            for ev in evs:
                if btn_back.clicked(ev):
                    self.tour = None
                    self.screen_stack = ["main"]
                    return
            return

        next_match = t.next_match()
        if next_match is None:
            t.advance()
            return

        ta, tb = next_match

        evs, mouse, _ = self.events_and_mouse()

        # Draw bracket status
        self.bg()
        self.title(f"🏆  Torneio — {t.round_name()}", 45)

        self._draw_bracket(t)

        # Show next match info
        panel_y = 420
        self.panel(pygame.Rect(cx - 320, panel_y, 640, 200))
        self.centered("PRÓXIMA PARTIDA", panel_y + 18, UI_ACCENT, self.fnt_mid)

        self.centered(ta.name, panel_y + 70, ta.color, self.fnt_big)
        self.centered("VS", panel_y + 115, GRAY, self.fnt_sm)
        self.centered(tb.name, panel_y + 148, tb.color, self.fnt_big)

        btn_play = Button(cx - 135, panel_y + 155, 270, 42, "▶  Jogar agora")
        btn_skip = Button(cx - 60,  panel_y + 155, 0, 0, "")  # unused

        if ta.is_human or tb.is_human:
            btn_play = Button(cx - 135, panel_y + 155, 270, 42, "▶  Jogar agora")
        else:
            btn_play = Button(cx - 135, panel_y + 155, 270, 42, "▷  Simular (IA)")

        btn_play.update(mouse)
        btn_play.draw(self.screen, self.fnt_sm)

        btn_menu = Button(cx - 80, 670, 160, 40, "← Menu", BTN_DANGER, BTN_DANGER_H)
        btn_menu.update(mouse)
        btn_menu.draw(self.screen, self.fnt_xs)

        for ev in evs:
            if btn_play.clicked(ev):
                self._run_tournament_match(ta, tb)
                return
            if btn_menu.clicked(ev):
                self.tour = None
                self.screen_stack = ["main"]
                return

    def _draw_bracket(self, t: Tournament):
        cx = SCREEN_W // 2
        panel_rect = pygame.Rect(50, 90, SCREEN_W - 100, 305)
        self.panel(panel_rect)

        if not t.matches:
            return

        cols = len(t.matches)
        slot_w = (panel_rect.width - 20) // max(cols, 1)
        slot_h = 50

        for i, (ta, tb) in enumerate(t.matches):
            sx = panel_rect.left + 10 + i * slot_w
            sy = 105

            # Team A slot
            pygame.draw.rect(self.screen, (30, 30, 70),
                             (sx, sy, slot_w - 6, slot_h - 4), border_radius=6)
            pygame.draw.rect(self.screen, ta.color,
                             (sx, sy, 6, slot_h - 4), border_radius=3)
            ns = self.fnt_xs.render(ta.name[:14], True,
                                    ta.color if ta.is_human else LIGHT_GRAY)
            self.screen.blit(ns, (sx + 10, sy + (slot_h - 4) // 2 - ns.get_height() // 2))

            # VS
            vs = self.fnt_xs.render("vs", True, GRAY)
            self.screen.blit(vs, (sx + slot_w // 2 - vs.get_width() // 2, sy + slot_h - 2))

            # Team B slot
            sy2 = sy + slot_h + 12
            pygame.draw.rect(self.screen, (30, 30, 70),
                             (sx, sy2, slot_w - 6, slot_h - 4), border_radius=6)
            pygame.draw.rect(self.screen, tb.color,
                             (sx, sy2, 6, slot_h - 4), border_radius=3)
            ns2 = self.fnt_xs.render(tb.name[:14], True,
                                     tb.color if tb.is_human else LIGHT_GRAY)
            self.screen.blit(ns2, (sx + 10, sy2 + (slot_h - 4) // 2 - ns2.get_height() // 2))

        # Past results
        if t.match_results:
            ry = 230
            self.label("Resultados anteriores:", 60, ry, UI_ACCENT, self.fnt_xs)
            for i, (winner, loser) in enumerate(t.match_results):
                ry += 22
                rs = self.fnt_xs.render(
                    f"✓ {winner.name}  derrota  {loser.name}", True, GREEN_COL)
                self.screen.blit(rs, (60, ry))

        # Round progress
        prog = self.fnt_xs.render(
            f"Partida {len(t.match_results) + 1} de {len(t.matches)}", True, GRAY)
        self.screen.blit(prog, (panel_rect.right - prog.get_width() - 10, 95))

    def _run_tournament_match(self, ta: TournamentTeam, tb: TournamentTeam):
        human_ctrl = "none"
        if ta.is_human and tb.is_human:
            human_ctrl = "both"
        elif ta.is_human:
            human_ctrl = "a"
        elif tb.is_human:
            human_ctrl = "b"

        mode = getattr(self, '_tour_mode', '1v1')

        m = Match(
            self.screen, self.clock,
            mode=mode,
            team_a_data=ta.players if ta.players else None,
            team_b_data=tb.players if tb.players else None,
            human_control=human_ctrl,
            ai_diff="normal",
            team_a_name=ta.name,
            team_b_name=tb.name,
            team_a_color=ta.color,
            team_b_color=tb.color,
        )
        result = m.run()

        if result == 'menu':
            return

        winner_team = ta if result['winner'] == 'a' else tb
        loser_team  = tb if result['winner'] == 'a' else ta
        self.tour.record_result(winner_team, loser_team)

        if self.tour.round_complete():
            self.tour.advance()

    def _draw_champion_screen(self, t: Tournament):
        self.bg()
        champ = t.champion
        self.title("🏆  CAMPEÃO!", 80, YELLOW)

        # Trophy area
        cx, cy = SCREEN_W // 2, SCREEN_H // 2
        self.panel(pygame.Rect(cx - 250, cy - 120, 500, 260))

        pygame.draw.circle(self.screen, YELLOW, (cx, cy - 40), 75, 5)
        pygame.draw.line(self.screen, YELLOW, (cx - 50, cy + 35), (cx + 50, cy + 35), 6)
        pygame.draw.line(self.screen, YELLOW, (cx, cy + 35), (cx, cy + 70), 6)

        name_s = self.fnt_big.render(champ.name, True, champ.color)
        self.screen.blit(name_s, name_s.get_rect(center=(cx, cy + 100)))

        msg = self.fnt_sm.render("Parabéns! Você conquistou o torneio!", True, LIGHT_GRAY)
        self.screen.blit(msg, msg.get_rect(center=(cx, cy + 145)))

    # ─────────────────────────────────────────────────────────────────────────
    # Main loop
    # ─────────────────────────────────────────────────────────────────────────

    def run(self):
        screen_map = {
            "main":              self.screen_main,
            "select_match":      self.screen_select_match,
            "create_player":     self.screen_create_player,
            "player_list":       self.screen_player_list,
            "tournament_setup":  self.screen_tournament_setup,
            "tournament":        self.screen_tournament,
        }

        while self.running:
            fn = screen_map.get(self.screen_stack[-1])
            if fn:
                fn()
            pygame.display.flip()
            self.clock.tick(FPS)

        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    Game().run()
