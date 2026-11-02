"""Typed declarations for one explicitly specified Survivor-style council."""

from dataclasses import dataclass
from enum import Enum
from typing import Annotated

from slimconfig import Output


class Tool(Enum):
    RESOLVE_VOTE = "resolve_vote"


class Task(Enum):
    ALLIANCE_SURVIVAL = "alliance-survival"


class TieRule(Enum):
    PRIORITY = "priority"
    REVOTE_PRIORITY = "revote_priority"
    REVOTE_ROCKS = "revote_rocks"


class Resolution(Enum):
    INITIAL_VOTE = "initial_vote"
    REVOTE = "revote"
    PRIORITY = "priority"
    ROCKS = "rocks"


@dataclass
class Ballot(Output):
    voter: Annotated[str, "An attending contestant, casting exactly one vote"]
    target: Annotated[str, "Another attending contestant"]


@dataclass
class VoteRules(Output):
    tie_rule: Annotated[TieRule, "priority, revote_priority, or revote_rocks; exact rules in README"]
    priority_order: Annotated[list[str], "Every contestant once; first eligible name loses a deadlock"]


@dataclass
class CouncilInput(Output):
    contestants: Annotated[list[str], "2 to 24 unique, case-sensitive names, in display order"]
    alliance: Annotated[list[str], "Nonempty subset; survival means every listed member remains"]
    votes: Annotated[list[Ballot], "Exactly one initial ballot per contestant; no self votes"]
    challenge_immune: Annotated[list[str], "Contestants who cannot receive any ballot"]
    idol_protected: Annotated[list[str], "Successful idol recipients; initial votes against them are nullified"]
    rules: VoteRules
    revotes: Annotated[list[Ballot], "For revote policies only: all initially non-tied contestants vote"]


@dataclass
class VoteCount(Output):
    contestant: str
    votes: int


@dataclass
class CouncilOutput(Output):
    eliminated: Annotated[str, "The single eliminated contestant"]
    alliance_survives: Annotated[bool, "True exactly when no alliance member is eliminated"]
    alliance_remaining: Annotated[list[str], "Remaining alliance members in contestants order"]
    initial_tally: Annotated[list[VoteCount], "Counted votes for every contestant, including zeros"]
    nullified_votes: Annotated[int, "Initial ballots discarded by idol protection"]
    revote_tally: Annotated[list[VoteCount], "Every contestant's count if a revote occurred; otherwise empty"]
    resolution: Resolution
    deciding_candidates: Annotated[list[str], "Final elimination candidates, in contestants order"]


TOOLS = {Tool.RESOLVE_VOTE: (CouncilInput, CouncilOutput)}
TASKS = {Task.ALLIANCE_SURVIVAL: (CouncilInput, CouncilOutput)}
