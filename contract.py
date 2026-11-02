"""Typed contract for Survivor votes, revotes, rocks, and final-four fire."""

from dataclasses import dataclass
from enum import Enum
from typing import Annotated

from slimconfig import Output


class Tool(Enum):
    RESOLVE_TRIBAL = "resolve_tribal"


class Task(Enum):
    SCENARIO_OUTCOME = "scenario-outcome"


class Resolution(Enum):
    INITIAL_VOTE = "initial_vote"
    REVOTE = "revote"
    ROCKS = "rocks"
    CONSENSUS = "consensus"
    FIRE = "fire"


class AdvantageKind(Enum):
    IDOL = "idol"
    EXTRA_VOTE = "extra_vote"
    VOTE_BLOCK = "vote_block"


class PersonalOutcome(Enum):
    NOT_SPECIFIED = "not_specified"
    YOU_GO_HOME = "you_go_home"
    ALLY_GOES_HOME = "ally_goes_home"
    ALLIANCE_SAFE = "alliance_safe"
    AWAITING_RESULT = "awaiting_result"


class CouncilFormat(Enum):
    STANDARD = "standard"
    FINAL_FOUR_VOTE = "final_four_vote"
    FINAL_FOUR_FIRE = "final_four_fire"


class CouncilStage(Enum):
    COMPLETE = "complete"
    REVOTE_REQUIRED = "revote_required"
    DEADLOCK = "deadlock"
    FIRE_REQUIRED = "fire_required"


class NeededFact(Enum):
    REVOTES = "revote_ballots"
    DEADLOCK_RESULT = "unanimous_decision_or_rock_result"
    FIRE_PAIR = "fire_making_pair"
    FIRE_WINNER = "fire_making_winner"


@dataclass
class Ballot(Output):
    voter: Annotated[str, "An attending contestant, casting exactly one vote"]
    target: Annotated[str, "Another attending contestant"]


@dataclass
class VoteCount(Output):
    contestant: str
    votes: int


@dataclass
class PlayedAdvantage(Output):
    id: Annotated[str, "Unique label for this single-use item, 1 to 40 printable trimmed characters"]
    owner: Annotated[str, "The contestant using the item; can be an ally or opponent"]
    kind: AdvantageKind
    target: Annotated[
        str,
        "Idol: protected RECIPIENT, which can differ from owner. Extra vote: additional ballot target. "
        "Vote block: contestant whose ordinary initial ballot is removed. Ask if the target is missing.",
    ]


@dataclass
class TribalCouncilInput(Output):
    contestants: Annotated[list[str], "2 to 24 unique names; this list's order is only for display"]
    alliance: Annotated[list[str], "Nonempty roster subset; supplied alliance labels are assumed facts"]
    votes: Annotated[
        list[Ballot],
        "One assumed ordinary initial vote per contestant before blocks/extras. Ballot order NEVER affects counting. "
        "For final_four_fire use []: that format has no vote.",
    ]
    challenge_immune: list[str]
    format: Annotated[
        CouncilFormat | None,
        "null means standard vote/revote/deadlock/rocks. Four people at a tribe is not automatically the final four. "
        "final_four_vote means a final-four vote with fire after a deadlocked revote. final_four_fire means the "
        "forced-fire format, with no vote. Use the format stated by the user.",
    ]
    revotes: Annotated[
        list[Ballot],
        "[] when unknown or unused. On an initial tie, only non-tied contestants revote, targeting tied contestants. "
        "The result reports missing revotes rather than inventing them.",
    ]


@dataclass
class ResolutionFacts(Output):
    consensus_eliminated: Annotated[str | None, "If specified, unanimous decision after a deadlocked revote"]
    rock_draw_loser: Annotated[str | None, "Only a stated actual/assumed rock result; never inferred from name order"]
    fire_participants: Annotated[
        list[str],
        "Two stated contestants making fire in forced final-four fire, or [] if unknown; the pair is unordered",
    ]
    fire_winner: Annotated[str | None, "Stated actual/assumed fire winner; null means do not predict the challenge"]


@dataclass
class TribalScenarioInput(Output):
    council: TribalCouncilInput
    plays: Annotated[list[PlayedAdvantage], "All assumed played items, including opponents'; [] for no plays"]
    perspective: Annotated[str | None, "User's named alliance member, or null when unidentified"]
    resolution_facts: Annotated[
        ResolutionFacts | None,
        "Use null unless the user has stated a deadlock decision, rock result, or fire details. "
        "Missing random/challenge outcomes remain unresolved; do not manufacture them.",
    ]


@dataclass
class TribalOutcome(Output):
    stage: CouncilStage
    eliminated: Annotated[str | None, "null until the supplied facts determine exactly who leaves"]
    alliance_survives: Annotated[bool | None, "null while unresolved; false is a valid calculated losing result"]
    alliance_remaining: list[str] | None
    initial_tally: list[VoteCount]
    nullified_votes: int
    revote_tally: list[VoteCount]
    resolution: Resolution | None
    tied_contestants: Annotated[list[str], "Initial tied contestants; they do not cast revote ballots"]
    revote_voters: list[str]
    rock_drawers: Annotated[list[str], "Deadlock drawers exclude initial tied contestants and protected contestants"]
    fire_contestants: list[str]
    needed_facts: list[NeededFact]


@dataclass
class TribalScenarioOutput(Output):
    scenario: TribalScenarioInput
    outcome: TribalOutcome
    personal_outcome: PersonalOutcome
    idol_recipients: list[str]
    blocked_voters: list[str]
    extra_votes: list[Ballot]


TOOLS = {Tool.RESOLVE_TRIBAL: (TribalScenarioInput, TribalScenarioOutput)}
TASKS = {Task.SCENARIO_OUTCOME: (TribalScenarioInput, TribalScenarioOutput)}
