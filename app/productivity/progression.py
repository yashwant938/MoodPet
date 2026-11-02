"""Central, deterministic evolution definitions. No Qt or persistence here."""
from bisect import bisect_right
from dataclasses import dataclass


@dataclass(frozen=True)
class Stage:
    name: str
    color: str
    landscape: str
    accessory: str


STAGES = (
    Stage('Seedling', '#75BE9B', 'Dewdrop meadow', 'Leaf antenna'),
    Stage('Explorer', '#73B6D8', 'Cloud islands', 'Explorer pack'),
    Stage('Builder', '#E6B368', 'Copper workshop', 'Maker helmet'),
    Stage('Warrior', '#D1848C', 'Ember ridge', 'Ember armor'),
    Stage('Guardian', '#72C4BE', 'Crystal sanctuary', 'Crystal shield'),
    Stage('Master', '#A69CDB', 'Twilight observatory', 'Astral hood'),
    Stage('Champion', '#E0C169', 'Sunlit arena', 'Laurel crest'),
    Stage('Conqueror', '#C58BC5', 'Violet citadel', 'Prism wings'),
    Stage('Mythic', '#81B2EC', 'Aurora sea', 'Aurora halo'),
    Stage('Legend', '#F2CE86', 'Celestial garden', 'Celestial crown'),
)


@dataclass(frozen=True)
class ProgressionRules:
    base_cost: int = 25
    cost_step: int = 2
    session_xp: int = 25
    task_xp: int = 10

    def __post_init__(self):
        if self.base_cost <= 0 or self.cost_step <= 0 or self.session_xp <= 0 or self.task_xp < 0:
            raise ValueError('Progression costs must increase and rewards must be nonnegative.')

    def cost(self, level: int) -> int:
        if not 1 <= level <= 100:
            raise ValueError('Global level must be 1–100')
        return self.base_cost + (level - 1) * self.cost_step

    def threshold(self, completed: int) -> int:
        if not 0 <= completed <= 100:
            raise ValueError('Completed levels must be 0–100')
        return completed * self.base_cost + self.cost_step * completed * (completed - 1) // 2


RULES = ProgressionRules()


@dataclass(frozen=True)
class Progress:
    xp: int
    completed: int
    global_level: int
    stage_index: int
    level: int
    earned: int
    required: int

    @property
    def stage(self) -> Stage:
        return STAGES[self.stage_index]

    @property
    def mastered(self) -> bool:
        return self.completed == 100

    @property
    def minor_upgrade(self) -> int:
        return min(2, max(0, (self.completed - self.stage_index * 10) // 3))


def progress_for(xp: int, rules: ProgressionRules = RULES) -> Progress:
    if not isinstance(xp, int) or xp < 0:
        raise ValueError('XP must be a nonnegative integer')
    completed = bisect_right([rules.threshold(n) for n in range(1, 101)], xp)
    rank = min(100, completed + 1)
    return Progress(xp, completed, rank, (rank - 1) // 10, (rank - 1) % 10 + 1,
                    xp - rules.threshold(rank - 1), rules.cost(rank))
