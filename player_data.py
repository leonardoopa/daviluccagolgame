import json
import os
from dataclasses import dataclass, asdict
from typing import List

DATA_FILE = os.path.join(os.path.dirname(__file__), "players.json")


@dataclass
class PlayerData:
    name: str
    age: int
    position: str
    height: float
    team: str
    jersey_number: int


def load_players() -> List[PlayerData]:
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [PlayerData(**p) for p in data]
    except Exception:
        return []


def save_players(players: List[PlayerData]):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump([asdict(p) for p in players], f, ensure_ascii=False, indent=2)


def add_player(player: PlayerData):
    players = load_players()
    players.append(player)
    save_players(players)


def delete_player(index: int):
    players = load_players()
    if 0 <= index < len(players):
        players.pop(index)
        save_players(players)
