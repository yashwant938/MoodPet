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
    Stage('Pioneer', '#E58E77', 'Comet outpost', 'Comet scarf'),
    Stage('Navigator', '#73BDB7', 'Lunar harbor', 'Navigator visor'),
    Stage('Artificer', '#DAAA6B', 'Solar forge', 'Solar gauntlets'),
    Stage('Sentinel', '#8CACE1', 'Sapphire fortress', 'Sentinel crest'),
    Stage('Sage', '#AABD85', 'Starlit library', 'Sage scroll'),
    Stage('Luminary', '#EDC26B', 'Radiant spires', 'Radiant aureole'),
    Stage('Ascendant', '#B791D2', 'Nebula crossing', 'Nebula fins'),
    Stage('Celestial', '#84CBE5', 'Orbit cathedral', 'Orbital rings'),
    Stage('Eternal', '#97C7A9', 'Timeless grove', 'Infinity sigil'),
    Stage('Infinity', '#E3AED2', 'Beyond the horizon', 'Prismatic diadem'),
)

LEVELS_PER_STAGE = 10
TOTAL_LEVELS = len(STAGES) * LEVELS_PER_STAGE


@dataclass(frozen=True)
class ProgressionRules:
    base_cost: int = 50
    cost_step: int = 2
    session_xp: int = 25
    task_xp: int = 10
    level_count: int = TOTAL_LEVELS

    def __post_init__(self):
        if any(type(value) is not int for value in (self.base_cost,self.cost_step,self.session_xp,self.task_xp,self.level_count)) or self.level_count < 1 or self.base_cost <= 0 or self.cost_step <= 0 or self.session_xp <= 0 or self.task_xp < 0:
            raise ValueError('Progression costs must increase and rewards must be nonnegative.')

    def cost(self, level: int) -> int:
        if not 1 <= level <= self.level_count:
            raise ValueError('Global level is outside the configured journey')
        return self.base_cost + (level - 1) * self.cost_step

    def threshold(self, completed: int) -> int:
        if not 0 <= completed <= self.level_count:
            raise ValueError('Completed levels are outside the configured journey')
        return completed * self.base_cost + self.cost_step * completed * (completed - 1) // 2


RULES = ProgressionRules()
RULES_V1 = ProgressionRules(base_cost=25, level_count=100)


@dataclass(frozen=True)
class Progress:
    xp: int
    completed: int
    global_level: int
    stage_index: int
    level: int
    earned: int
    required: int
    level_count: int = TOTAL_LEVELS
    curve_credit: int = 0

    @property
    def stage(self) -> Stage:
        return STAGES[self.stage_index]

    @property
    def mastered(self) -> bool:
        return self.completed == self.level_count

    @property
    def minor_upgrade(self) -> int:
        return min(2, max(0, (self.completed - self.stage_index * 10) // 3))


def progress_for(xp: int, rules: ProgressionRules = RULES, credit: int = 0) -> Progress:
    if not isinstance(xp, int) or xp < 0 or not isinstance(credit,int) or credit < 0:
        raise ValueError('XP must be a nonnegative integer')
    effective = xp + credit
    completed = bisect_right([rules.threshold(n) for n in range(1, rules.level_count + 1)], effective)
    rank = min(rules.level_count, completed + 1)
    return Progress(xp, completed, rank, (rank - 1) // LEVELS_PER_STAGE, (rank - 1) % LEVELS_PER_STAGE + 1,
                    effective - rules.threshold(rank - 1), rules.cost(rank), rules.level_count, credit)
