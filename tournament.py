import random
from constants import *


class TournamentTeam:
    def __init__(self, name, color, is_human=False, players=None):
        self.name = name
        self.color = color
        self.is_human = is_human
        self.players = players or []


class Tournament:
    """
    8-team single-elimination bracket.
    Oitavas (4 matches) → Quartas (2 matches) → Semi (1 match) → Final
    Rounds keep halving until 1 champion.
    """

    ROUND_NAMES = ["Oitavas de Final", "Quartas de Final", "Semifinal", "Final"]

    AI_NAMES = [
        "Leões FC", "Tubarões", "Águias SC",
        "Panteras", "Cobras FC", "Tigres",
        "Gaviões EC",
    ]
    AI_COLORS = [BLUE, GREEN_COL, ORANGE, PURPLE, CYAN, (255, 90, 90), YELLOW]

    def __init__(self, human_team_name, human_players=None, human_color=None):
        self.human = TournamentTeam(
            human_team_name,
            human_color or RED,
            is_human=True,
            players=human_players or [],
        )

        ai_teams = [
            TournamentTeam(self.AI_NAMES[i], self.AI_COLORS[i])
            for i in range(7)
        ]

        all_teams = [self.human] + ai_teams
        random.shuffle(all_teams)

        self.current_round = 0
        self.round_teams = all_teams  # 8 teams to start
        self.champion = None
        self.bracket_history = []   # list of rounds, each round = list of (winner, loser)

        self._build_matches()

    def _build_matches(self):
        teams = self.round_teams
        self.matches = [(teams[i * 2], teams[i * 2 + 1])
                        for i in range(len(teams) // 2)]
        self.match_results = []  # filled as matches are played

    def round_name(self):
        idx = min(self.current_round, len(self.ROUND_NAMES) - 1)
        return self.ROUND_NAMES[idx]

    def next_match(self):
        """Return the next unplayed (team_a, team_b) pair, or None if round done."""
        idx = len(self.match_results)
        if idx < len(self.matches):
            return self.matches[idx]
        return None

    def record_result(self, winner_team, loser_team):
        self.match_results.append((winner_team, loser_team))

    def advance(self):
        """Move to next round with winners. Call after all matches played."""
        winners = [w for w, _ in self.match_results]
        self.bracket_history.append(list(zip(self.matches, self.match_results)))
        self.round_teams = winners
        self.current_round += 1

        if len(self.round_teams) == 1:
            self.champion = self.round_teams[0]
        else:
            self._build_matches()

    def round_complete(self):
        return len(self.match_results) == len(self.matches)

    def is_done(self):
        return self.champion is not None

    def human_in_next_match(self):
        m = self.next_match()
        if m is None:
            return False
        return m[0].is_human or m[1].is_human
