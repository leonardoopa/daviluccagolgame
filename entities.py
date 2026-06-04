import pygame
import math
from constants import *


class Ball:
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.vx = 0.0
        self.vy = 0.0
        self.radius = BALL_RADIUS
        self.last_touched = None

    def reset(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.vx = 0.0
        self.vy = 0.0

    def update(self):
        self.vy += GRAVITY
        self.x += self.vx
        self.y += self.vy

        if self.y + self.radius >= FIELD_BOTTOM:
            self.y = FIELD_BOTTOM - self.radius
            self.vy = -abs(self.vy) * BALL_BOUNCE
            if abs(self.vy) < 1.5:
                self.vy = 0
            self.vx *= 0.88

        if self.y - self.radius <= FIELD_TOP:
            self.y = FIELD_TOP + self.radius
            self.vy = abs(self.vy) * BALL_BOUNCE

        self.vx *= BALL_FRICTION
        if abs(self.vx) < 0.08:
            self.vx = 0.0

    def apply_wall_bounce(self, side):
        """side: 'left' or 'right' — bounce off field edge (not goal)."""
        if side == 'left':
            self.x = FIELD_LEFT + self.radius
            self.vx = abs(self.vx) * BALL_BOUNCE
        else:
            self.x = FIELD_RIGHT - self.radius
            self.vx = -abs(self.vx) * BALL_BOUNCE

    def draw(self, surface):
        ix, iy = int(self.x), int(self.y)
        r = self.radius
        shadow_surf = pygame.Surface((r * 4, 12), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surf, (0, 0, 0, 90), shadow_surf.get_rect())
        surface.blit(shadow_surf, (ix - r * 2, FIELD_BOTTOM - 8))
        pygame.draw.circle(surface, BALL_COL, (ix, iy), r)
        pygame.draw.circle(surface, BALL_MARK, (ix, iy), r, 2)
        # Hex pattern dots
        offsets = [(0, -r//2), (r//2, r//4), (-r//2, r//4)]
        for ox, oy in offsets:
            pygame.draw.circle(surface, BALL_MARK, (ix + ox, iy + oy), r // 5)


class PlayerSprite:
    def __init__(self, x, y, team, shirt_color, facing_right=True, is_goalkeeper=False):
        self.x = float(x)
        self.y = float(y)
        self.vx = 0.0
        self.vy = 0.0
        self.w = PLAYER_W
        self.h = PLAYER_H
        self.team = team
        self.shirt_color = shirt_color
        self.facing_right = facing_right
        self.on_ground = False
        self.is_goalkeeper = is_goalkeeper
        self.kick_cd = 0
        self.name = ""
        self.jersey_number = 0
        self.walk_frame = 0
        self.walk_timer = 0
        self._field_left = FIELD_LEFT
        self._field_right = FIELD_RIGHT

    @property
    def cx(self):
        return self.x

    @property
    def cy(self):
        return self.y - self.h * 0.5

    @property
    def rect(self):
        return pygame.Rect(int(self.x - self.w // 2), int(self.y - self.h), self.w, self.h)

    def set_field_bounds(self, left, right):
        self._field_left = left
        self._field_right = right

    def move_left(self):
        self.vx = -PLAYER_SPEED
        self.facing_right = False

    def move_right(self):
        self.vx = PLAYER_SPEED
        self.facing_right = True

    def jump(self):
        if self.on_ground:
            self.vy = JUMP_FORCE
            self.on_ground = False

    def try_kick(self, ball: Ball):
        if self.kick_cd > 0:
            return False
        dx = ball.x - self.cx
        dy = ball.y - self.cy
        dist = math.hypot(dx, dy)
        kick_range = self.w * 1.1 + ball.radius
        if dist < kick_range:
            if dist > 0:
                nx, ny = dx / dist, dy / dist
            else:
                nx, ny = (1 if self.facing_right else -1), -0.3
            ball.vx = nx * KICK_FORCE + self.vx * 0.4
            ball.vy = ny * KICK_FORCE - 1.5
            ball.last_touched = self.team
            self.kick_cd = 22
            return True
        return False

    def auto_kick(self, ball: Ball, goal_dir: int):
        """AI kick toward goal_dir (-1=left, +1=right)."""
        if self.kick_cd > 0:
            return False
        dx = ball.x - self.cx
        dy = ball.y - self.cy
        if math.hypot(dx, dy) < self.w * 1.3 + ball.radius:
            ball.vx = goal_dir * KICK_FORCE * 1.05
            ball.vy = -KICK_FORCE * 0.45
            ball.last_touched = self.team
            self.kick_cd = 22
            return True
        return False

    def collide_with_ball(self, ball: Ball):
        dx = ball.x - self.cx
        dy = ball.y - self.cy
        dist = math.hypot(dx, dy)
        min_dist = self.w * 0.58 + ball.radius
        if dist < min_dist and dist > 0:
            nx, ny = dx / dist, dy / dist
            overlap = min_dist - dist
            ball.x += nx * overlap * 0.85
            ball.y += ny * overlap * 0.85
            dot = ball.vx * nx + ball.vy * ny
            if dot < 0:
                ball.vx -= dot * nx * (1 + BALL_BOUNCE)
                ball.vy -= dot * ny * (1 + BALL_BOUNCE)
            ball.vx += self.vx * 0.25
            ball.last_touched = self.team

    def update(self):
        self.vy += GRAVITY
        self.x += self.vx
        self.y += self.vy

        self.vx *= 0.78

        if self.y >= FIELD_BOTTOM:
            self.y = FIELD_BOTTOM
            self.vy = 0
            self.on_ground = True
        else:
            self.on_ground = False

        if self.y - self.h < FIELD_TOP:
            self.y = FIELD_TOP + self.h
            self.vy = 0

        half_w = self.w // 2
        if self.x - half_w < self._field_left:
            self.x = self._field_left + half_w
            self.vx = 0
        if self.x + half_w > self._field_right:
            self.x = self._field_right - half_w
            self.vx = 0

        if self.kick_cd > 0:
            self.kick_cd -= 1

        if abs(self.vx) > 0.5:
            self.walk_timer += 1
            if self.walk_timer >= 7:
                self.walk_timer = 0
                self.walk_frame = (self.walk_frame + 1) % 4
        else:
            self.walk_frame = 0

    def draw(self, surface, font_small=None):
        cx = int(self.x)
        fy = int(self.y)
        w, h = self.w, self.h

        # Shadow
        sh = pygame.Surface((w * 2, 10), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0, 0, 0, 70), sh.get_rect())
        surface.blit(sh, (cx - w, FIELD_BOTTOM - 6))

        # Legs
        leg_w, leg_h = w // 4, h // 3
        leg_y = fy - h // 3
        leg_off = 0
        if self.walk_frame == 1:
            leg_off = 6
        elif self.walk_frame == 3:
            leg_off = -6

        sock_col = tuple(max(0, c - 80) for c in self.shirt_color)
        pygame.draw.rect(surface, SKIN, (cx - w // 2 + 2, leg_y + leg_off, leg_w, leg_h), border_radius=3)
        pygame.draw.rect(surface, SKIN, (cx + 2, leg_y - leg_off, leg_w, leg_h), border_radius=3)
        pygame.draw.rect(surface, sock_col, (cx - w // 2 + 2, leg_y + leg_off + leg_h - 8, leg_w, 8), border_radius=2)
        pygame.draw.rect(surface, sock_col, (cx + 2, leg_y - leg_off + leg_h - 8, leg_w, 8), border_radius=2)

        # Shorts
        shorts_col = tuple(max(0, c - 55) for c in self.shirt_color)
        shorts_rect = pygame.Rect(cx - w // 2, fy - h // 3 - 2, w, h // 5)
        pygame.draw.rect(surface, shorts_col, shorts_rect, border_radius=3)

        # Shirt (body)
        body_rect = pygame.Rect(cx - w // 2, fy - h + 1, w, h * 2 // 3)
        pygame.draw.rect(surface, self.shirt_color, body_rect, border_radius=6)

        # Jersey number on shirt
        if self.jersey_number and font_small:
            num_s = font_small.render(str(self.jersey_number), True, WHITE)
            surface.blit(num_s, num_s.get_rect(center=(cx, fy - h // 2)))

        # Head
        head_r = w // 2 + 1
        head_y = fy - h + head_r - 2
        pygame.draw.circle(surface, SKIN, (cx, head_y), head_r)

        # Hair
        hair_col = (50, 35, 15)
        pygame.draw.arc(surface, hair_col,
                        (cx - head_r, head_y - head_r, head_r * 2, head_r),
                        math.pi * 0.05, math.pi * 0.95, 5)

        # Eyes
        eye_dir = 4 if self.facing_right else -4
        pygame.draw.circle(surface, BLACK, (cx + eye_dir, head_y), 3)

        # Name tag above head
        if self.name and font_small:
            ns = font_small.render(self.name, True, WHITE)
            nr = ns.get_rect(center=(cx, fy - h - 6))
            bg = pygame.Surface((nr.width + 6, nr.height + 2), pygame.SRCALPHA)
            bg.fill((0, 0, 0, 130))
            surface.blit(bg, (nr.x - 3, nr.y - 1))
            surface.blit(ns, nr)
