import pygame
import math
import random
import sys
from constants import *
from entities import Ball, PlayerSprite
from ai import AIController


class Match:
    """
    Runs a single match.

    human_control: 'both' | 'a' | 'b' | 'none'
    mode: '1v1' | '2v2'
    """

    S_KICKOFF = "kickoff"
    S_PLAYING = "playing"
    S_GOAL    = "goal"
    S_DONE    = "done"

    def __init__(self, screen, clock, mode="1v1",
                 team_a_data=None, team_b_data=None,
                 human_control="both", ai_diff="normal",
                 team_a_name="Time A", team_b_name="Time B",
                 team_a_color=None, team_b_color=None):

        self.screen = screen
        self.clock = clock
        self.mode = mode
        self.human_control = human_control
        self.goals_to_win = GOALS_TO_WIN

        self.score_a = 0
        self.score_b = 0
        self.state = self.S_KICKOFF
        self.goal_timer = 0
        self.kickoff_timer = 100
        self.winner = None
        self.last_scorer = None

        self.team_a_name = team_a_name
        self.team_b_name = team_b_name
        self.col_a = team_a_color or RED
        self.col_b = team_b_color or BLUE

        cx = (FIELD_LEFT + FIELD_RIGHT) // 2
        self.center_x = cx
        self.goal_y = FIELD_BOTTOM - GOAL_HEIGHT

        num = 1 if mode == "1v1" else 2

        self.players_a = self._make_team(
            'a', self.col_a, True, num, team_a_data,
            start_x=cx - 220, step=-130
        )
        self.players_b = self._make_team(
            'b', self.col_b, False, num, team_b_data,
            start_x=cx + 220, step=130
        )

        self.ai = {}
        self._setup_ai(ai_diff, num)

        self.ball = Ball(cx, FIELD_BOTTOM - 60)
        self.particles = []

        self.font_hud = pygame.font.SysFont("arial", 68, bold=True)
        self.font_mid = pygame.font.SysFont("arial", 44, bold=True)
        self.font_sm  = pygame.font.SysFont("arial", 22)
        self.font_xs  = pygame.font.SysFont("arial", 15)

        self.field_surf = self._build_field()

    # ── Setup ────────────────────────────────────────────────────────────────

    def _make_team(self, team, color, facing_right, num, player_data, start_x, step):
        sprites = []
        for i in range(num):
            is_gk = (i == num - 1 and num == 2)
            x = start_x + i * step
            p = PlayerSprite(x, FIELD_BOTTOM, team, color, facing_right, is_gk)
            # Confine team A to left half, team B to right half so goalkeepers work
            if team == 'a':
                p.set_field_bounds(FIELD_LEFT, self.center_x + 80)
            else:
                p.set_field_bounds(self.center_x - 80, FIELD_RIGHT)
            if player_data and i < len(player_data):
                pd = player_data[i]
                p.name = pd.name[:9]
                p.jersey_number = pd.jersey_number
            else:
                p.name = f"J{i+1}"
                p.jersey_number = i + 1
            sprites.append(p)
        return sprites

    def _setup_ai(self, diff, num):
        if self.human_control in ('b', 'none'):
            for p in self.players_a:
                self.ai[id(p)] = AIController(diff)
        if self.human_control in ('a', 'none'):
            for p in self.players_b:
                self.ai[id(p)] = AIController(diff)
        if num == 2:
            if self.human_control in ('both', 'a') and len(self.players_a) > 1:
                self.ai[id(self.players_a[1])] = AIController(diff)
            if self.human_control in ('both', 'b') and len(self.players_b) > 1:
                self.ai[id(self.players_b[1])] = AIController(diff)

    def _build_field(self):
        surf = pygame.Surface((SCREEN_W, SCREEN_H))
        surf.fill(DARK_BG)

        fw = FIELD_RIGHT - FIELD_LEFT
        stripe_w = fw // 8
        for i in range(8):
            col = FIELD_COL if i % 2 == 0 else FIELD_DARK
            r = pygame.Rect(FIELD_LEFT + i * stripe_w, FIELD_TOP, stripe_w, FIELD_BOTTOM - FIELD_TOP)
            pygame.draw.rect(surf, col, r)

        field_rect = pygame.Rect(FIELD_LEFT, FIELD_TOP, fw, FIELD_BOTTOM - FIELD_TOP)
        pygame.draw.rect(surf, LINE_COL, field_rect, 3)

        cx = self.center_x
        pygame.draw.line(surf, LINE_COL, (cx, FIELD_TOP), (cx, FIELD_BOTTOM), 2)
        mid_y = (FIELD_TOP + FIELD_BOTTOM) // 2
        pygame.draw.circle(surf, LINE_COL, (cx, mid_y), 85, 2)
        pygame.draw.circle(surf, LINE_COL, (cx, mid_y), 5)

        gy = self.goal_y
        gh = GOAL_HEIGHT
        gd = GOAL_DEPTH

        # Left goal posts
        pygame.draw.line(surf, NET_COL, (FIELD_LEFT, gy), (FIELD_LEFT - gd, gy), 3)
        pygame.draw.line(surf, NET_COL, (FIELD_LEFT, FIELD_BOTTOM), (FIELD_LEFT - gd, FIELD_BOTTOM), 3)
        pygame.draw.line(surf, NET_COL, (FIELD_LEFT - gd, gy), (FIELD_LEFT - gd, FIELD_BOTTOM), 3)

        # Right goal posts
        pygame.draw.line(surf, NET_COL, (FIELD_RIGHT, gy), (FIELD_RIGHT + gd, gy), 3)
        pygame.draw.line(surf, NET_COL, (FIELD_RIGHT, FIELD_BOTTOM), (FIELD_RIGHT + gd, FIELD_BOTTOM), 3)
        pygame.draw.line(surf, NET_COL, (FIELD_RIGHT + gd, gy), (FIELD_RIGHT + gd, FIELD_BOTTOM), 3)

        net_col2 = (170, 170, 170)
        for i in range(1, 7):
            y = gy + i * (gh // 7)
            pygame.draw.line(surf, net_col2, (FIELD_LEFT - gd, y), (FIELD_LEFT, y), 1)
            pygame.draw.line(surf, net_col2, (FIELD_RIGHT, y), (FIELD_RIGHT + gd, y), 1)
        for i in range(1, 3):
            xl = FIELD_LEFT - gd + i * (gd // 3)
            xr = FIELD_RIGHT + i * (gd // 3)
            pygame.draw.line(surf, net_col2, (xl, gy), (xl, FIELD_BOTTOM), 1)
            pygame.draw.line(surf, net_col2, (xr, gy), (xr, FIELD_BOTTOM), 1)

        # Penalty areas
        pw, ph = 160, 95
        pygame.draw.rect(surf, LINE_COL, (FIELD_LEFT, FIELD_BOTTOM - ph, pw, ph), 1)
        pygame.draw.rect(surf, LINE_COL, (FIELD_RIGHT - pw, FIELD_BOTTOM - ph, pw, ph), 1)

        # Score bar background
        pygame.draw.rect(surf, UI_BG, (0, 0, SCREEN_W, FIELD_TOP))
        pygame.draw.line(surf, UI_ACCENT, (0, FIELD_TOP - 1), (SCREEN_W, FIELD_TOP - 1), 2)

        return surf

    # ── Reset ────────────────────────────────────────────────────────────────

    def _reset(self):
        cx = self.center_x
        self.ball.reset(cx, FIELD_BOTTOM - 60)

        num = len(self.players_a)
        for i, p in enumerate(self.players_a):
            p.x = float(cx - 220 - i * 130)
            p.y = float(FIELD_BOTTOM)
            p.vx = p.vy = 0
        for i, p in enumerate(self.players_b):
            p.x = float(cx + 220 + i * 130)
            p.y = float(FIELD_BOTTOM)
            p.vx = p.vy = 0

        self.state = self.S_KICKOFF
        self.kickoff_timer = 100

    # ── Goal detection ────────────────────────────────────────────────────────

    def _check_goal(self):
        bx, by = self.ball.x, self.ball.y
        in_goal_height = self.goal_y <= by <= FIELD_BOTTOM + self.ball.radius

        if bx - self.ball.radius <= FIELD_LEFT - GOAL_DEPTH and in_goal_height:
            return 'b'
        if bx + self.ball.radius >= FIELD_RIGHT + GOAL_DEPTH and in_goal_height:
            return 'a'
        return None

    # ── Input ─────────────────────────────────────────────────────────────────

    def handle_input(self, events, keys):
        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return 'menu'

        if self.state != self.S_PLAYING:
            return None

        if self.human_control in ('a', 'both') and self.players_a:
            p = self.players_a[0]
            if keys[pygame.K_a] or keys[pygame.K_LEFT]:
                pass  # handled per team below
            if keys[pygame.K_a]:
                p.move_left()
            elif keys[pygame.K_d]:
                p.move_right()
            if keys[pygame.K_w]:
                p.jump()
            if keys[pygame.K_SPACE]:
                p.try_kick(self.ball)

        if self.human_control in ('b', 'both') and self.players_b:
            p = self.players_b[0]
            if keys[pygame.K_LEFT]:
                p.move_left()
            elif keys[pygame.K_RIGHT]:
                p.move_right()
            if keys[pygame.K_UP]:
                p.jump()
            if keys[pygame.K_RETURN] or keys[pygame.K_RSHIFT] or keys[pygame.K_KP0]:
                p.try_kick(self.ball)

        return None

    # ── Update ────────────────────────────────────────────────────────────────

    def update(self):
        if self.state == self.S_KICKOFF:
            self.kickoff_timer -= 1
            # Keep ball physics alive so it settles on the spot instead of
            # floating frozen in the air during the countdown.
            self.ball.update()
            if self.kickoff_timer <= 0:
                self.state = self.S_PLAYING
            return

        if self.state == self.S_GOAL:
            self.goal_timer -= 1
            # Let the ball fall naturally during the celebration (no "frozen
            # in mid-air / lost gravity" look).
            self.ball.update()
            self._tick_particles()
            if self.goal_timer <= 0:
                if self.score_a >= self.goals_to_win or self.score_b >= self.goals_to_win:
                    self.winner = 'a' if self.score_a >= self.goals_to_win else 'b'
                    self.state = self.S_DONE
                else:
                    self._reset()
            return

        if self.state == self.S_DONE:
            self.ball.update()
            return

        # AI
        for p in self.players_a:
            ctrl = self.ai.get(id(p))
            if ctrl:
                ctrl.update(p, self.ball, FIELD_RIGHT, FIELD_LEFT)
        for p in self.players_b:
            ctrl = self.ai.get(id(p))
            if ctrl:
                ctrl.update(p, self.ball, FIELD_LEFT, FIELD_RIGHT)

        all_p = self.players_a + self.players_b

        for p in all_p:
            p.update()
            p.collide_with_ball(self.ball)

        self._push_players_apart()

        self.ball.update()

        # Wall bounce only outside goal height
        in_goal_h = self.goal_y <= self.ball.y <= FIELD_BOTTOM + self.ball.radius
        if self.ball.x - self.ball.radius < FIELD_LEFT and not in_goal_h:
            self.ball.apply_wall_bounce('left')
        if self.ball.x + self.ball.radius > FIELD_RIGHT and not in_goal_h:
            self.ball.apply_wall_bounce('right')

        scorer = self._check_goal()
        if scorer:
            if scorer == 'a':
                self.score_a += 1
            else:
                self.score_b += 1
            self.last_scorer = scorer
            self.state = self.S_GOAL
            self.goal_timer = 120
            self._spawn_particles()

        self._tick_particles()

    def _push_players_apart(self):
        all_p = self.players_a + self.players_b
        for i, p1 in enumerate(all_p):
            for p2 in all_p[i + 1:]:
                dx = p2.x - p1.x
                if abs(dx) < p1.w and abs(p2.y - p1.y) < 20:
                    push = (p1.w - abs(dx)) * 0.5
                    if dx >= 0:
                        p1.x -= push; p2.x += push
                    else:
                        p1.x += push; p2.x -= push

    # ── Particles ────────────────────────────────────────────────────────────

    def _spawn_particles(self):
        col = self.col_a if self.last_scorer == 'a' else self.col_b
        gx = FIELD_RIGHT if self.last_scorer == 'a' else FIELD_LEFT
        for _ in range(50):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(3, 14)
            self.particles.append({
                'x': float(gx), 'y': float(self.goal_y + GOAL_HEIGHT // 2),
                'vx': math.cos(angle) * speed,
                'vy': math.sin(angle) * speed - 2,
                'life': random.randint(35, 90),
                'color': col,
                'size': random.randint(4, 13),
            })

    def _tick_particles(self):
        for p in self.particles[:]:
            p['x'] += p['vx']
            p['y'] += p['vy']
            p['vy'] += 0.35
            p['life'] -= 1
            if p['life'] <= 0:
                self.particles.remove(p)

    # ── Draw ─────────────────────────────────────────────────────────────────

    def draw(self):
        self.screen.blit(self.field_surf, (0, 0))

        for pt in self.particles:
            pygame.draw.circle(self.screen, pt['color'], (int(pt['x']), int(pt['y'])), pt['size'])

        for p in self.players_a + self.players_b:
            p.draw(self.screen, self.font_xs)

        self.ball.draw(self.screen)
        self._draw_hud()

        if self.state == self.S_KICKOFF:
            self._overlay_kickoff()
        elif self.state == self.S_GOAL:
            self._overlay_goal()
        elif self.state == self.S_DONE:
            self._overlay_done()

    def _draw_hud(self):
        # Team A name & score
        a_name = self.font_xs.render(self.team_a_name, True, self.col_a)
        self.screen.blit(a_name, a_name.get_rect(center=(SCREEN_W // 2 - 130, 20)))

        score_a = self.font_hud.render(str(self.score_a), True, self.col_a)
        self.screen.blit(score_a, score_a.get_rect(center=(SCREEN_W // 2 - 60, 42)))

        sep = self.font_hud.render(":", True, WHITE)
        self.screen.blit(sep, sep.get_rect(center=(SCREEN_W // 2, 42)))

        score_b = self.font_hud.render(str(self.score_b), True, self.col_b)
        self.screen.blit(score_b, score_b.get_rect(center=(SCREEN_W // 2 + 60, 42)))

        b_name = self.font_xs.render(self.team_b_name, True, self.col_b)
        self.screen.blit(b_name, b_name.get_rect(center=(SCREEN_W // 2 + 130, 20)))

        goal_txt = self.font_xs.render(f"Primeiro a {self.goals_to_win} gols", True, GRAY)
        self.screen.blit(goal_txt, goal_txt.get_rect(center=(SCREEN_W // 2, 66)))

        ctrl_a = self.font_xs.render("WASD + ESPAÇO", True, self.col_a)
        self.screen.blit(ctrl_a, (8, 10))
        ctrl_b = self.font_xs.render("← → ↑ + ENTER", True, self.col_b)
        self.screen.blit(ctrl_b, (SCREEN_W - ctrl_b.get_width() - 8, 10))
        esc_s = self.font_xs.render("ESC=Menu", True, GRAY)
        self.screen.blit(esc_s, (8, 28))

    def _draw_overlay(self, alpha=140):
        ov = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        ov.fill((0, 0, 0, alpha))
        self.screen.blit(ov, (0, 0))

    def _overlay_kickoff(self):
        # Countdown 3 -> 2 -> 1 spanning the WHOLE kickoff so the field is
        # never just sitting there frozen with no feedback.
        self._draw_overlay(70)
        n = max(1, min(3, self.kickoff_timer // 34 + 1))
        c = self.font_hud.render(str(n), True, YELLOW)
        self.screen.blit(c, c.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 - 10)))
        sub = self.font_sm.render("Preparar...", True, LIGHT_GRAY)
        self.screen.blit(sub, sub.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 + 55)))

    def _overlay_goal(self):
        self._draw_overlay(110)
        col = self.col_a if self.last_scorer == 'a' else self.col_b
        name = self.team_a_name if self.last_scorer == 'a' else self.team_b_name

        g = self.font_hud.render("G O O O O L !", True, YELLOW)
        n = self.font_mid.render(name, True, col)
        s = self.font_mid.render(f"{self.score_a}  :  {self.score_b}", True, WHITE)

        cy = SCREEN_H // 2
        self.screen.blit(g, g.get_rect(center=(SCREEN_W // 2, cy - 70)))
        self.screen.blit(n, n.get_rect(center=(SCREEN_W // 2, cy)))
        self.screen.blit(s, s.get_rect(center=(SCREEN_W // 2, cy + 60)))

    def _overlay_done(self):
        self._draw_overlay(155)
        col = self.col_a if self.winner == 'a' else self.col_b
        name = self.team_a_name if self.winner == 'a' else self.team_b_name

        w  = self.font_hud.render("VENCEDOR!", True, YELLOW)
        n  = self.font_mid.render(name, True, col)
        s  = self.font_mid.render(f"{self.score_a}  :  {self.score_b}", True, WHITE)
        ct = self.font_sm.render("Pressione ENTER para continuar", True, LIGHT_GRAY)

        cy = SCREEN_H // 2
        self.screen.blit(w,  w.get_rect(center=(SCREEN_W // 2, cy - 90)))
        self.screen.blit(n,  n.get_rect(center=(SCREEN_W // 2, cy - 20)))
        self.screen.blit(s,  s.get_rect(center=(SCREEN_W // 2, cy + 50)))
        self.screen.blit(ct, ct.get_rect(center=(SCREEN_W // 2, cy + 110)))

    # ── Main loop ────────────────────────────────────────────────────────────

    def run(self):
        """Run match loop. Returns dict with winner/scores, or 'menu'."""
        self._reset()
        while True:
            events = pygame.event.get()
            keys = pygame.key.get_pressed()

            for ev in events:
                if ev.type == pygame.QUIT:
                    pygame.quit(); sys.exit()

            action = self.handle_input(events, keys)
            if action == 'menu':
                return 'menu'

            if self.state == self.S_DONE:
                for ev in events:
                    if ev.type == pygame.KEYDOWN and ev.key == pygame.K_RETURN:
                        return {'winner': self.winner,
                                'score_a': self.score_a,
                                'score_b': self.score_b}

            self.update()
            self.draw()
            pygame.display.flip()
            self.clock.tick(FPS)
