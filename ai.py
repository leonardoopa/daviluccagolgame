import math
import random
from constants import *


class AIController:
    """Heuristic AI for a PlayerSprite."""

    DELAYS = {"facil": 12, "normal": 6, "dificil": 2}

    def __init__(self, difficulty="normal"):
        self.difficulty = difficulty
        self.reaction_delay = self.DELAYS.get(difficulty, 6)
        self.timer = 0
        self.target_x = None

    def update(self, player, ball, opp_goal_x, own_goal_x):
        self.timer += 1
        if self.timer < self.reaction_delay:
            return
        self.timer = 0

        # Easy AI makes occasional mistakes
        if self.difficulty == "facil" and random.random() < 0.08:
            return

        bx, by = ball.x, ball.y
        px, py = player.cx, player.cy
        goal_dir = 1 if opp_goal_x > own_goal_x else -1
        dist_to_ball = math.hypot(bx - px, by - py)

        if player.is_goalkeeper:
            self._goalkeeper_logic(player, ball, own_goal_x, goal_dir, dist_to_ball)
        else:
            self._outfield_logic(player, ball, own_goal_x, opp_goal_x, goal_dir, dist_to_ball)

    def _goalkeeper_logic(self, player, ball, own_goal_x, goal_dir, dist):
        bx, by = ball.x, ball.y
        px = player.cx

        if dist < 220:
            # Chase ball
            if bx - px > 15:
                player.move_right()
            elif bx - px < -15:
                player.move_left()
            if by < player.cy - 40 and dist < 180:
                player.jump()
            player.try_kick(ball) or player.auto_kick(ball, goal_dir)
        else:
            # Hover near goal x
            target = own_goal_x + (-40 if goal_dir == 1 else 40)
            if px - target > 18:
                player.move_left()
            elif target - px > 18:
                player.move_right()

    def _outfield_logic(self, player, ball, own_goal_x, opp_goal_x, goal_dir, dist):
        bx, by = ball.x, ball.y
        px, py = player.cx, player.cy

        # Move toward ball
        if bx - px > 14:
            player.move_right()
        elif bx - px < -14:
            player.move_left()

        # Jump when ball is higher or to head it
        if by < py - 28 and dist < 200:
            player.jump()

        if not player.try_kick(ball):
            player.auto_kick(ball, goal_dir)
