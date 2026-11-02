"""Typed declarations for one explicitly specified Survivor-style council."""

from dataclasses import dataclass
from enum import Enum
from typing import Annotated

from slimconfig import Output


class Tool(Enum):
    EVALUATE_SCENARIO = "evaluate_scenario"
    RESOLVE_VOTE = "resolve_vote"
    FIND_RESCUE = "find_rescue"
    PLAN_ADVANTAGES = "plan_advantages"


class Task(Enum):
    SCENARIO_OUTCOME = "scenario-outcome"
    ALLIANCE_SURVIVAL = "alliance-survival"
    SINGLE_VOTE_RESCUE = "single-vote-rescue"
    ADVANTAGE_PLANNER = "advantage-planner"


class TieRule(Enum):
    PRIORITY = "priority"
    REVOTE_PRIORITY = "revote_priority"
    REVOTE_ROCKS = "revote_rocks"


class Resolution(Enum):
    INITIAL_VOTE = "initial_vote"
    REVOTE = "revote"
    PRIORITY = "priority"
    ROCKS = "rocks"


class RescueStatus(Enum):
    ALREADY_SAFE = "already_safe"
    RESCUABLE = "rescuable"
    IMPOSSIBLE = "impossible"


class AdvantageKind(Enum):
    IDOL = "idol"
    EXTRA_VOTE = "extra_vote"
    VOTE_BLOCK = "vote_block"


class AdvantageDecision(Enum):
    HOLD = "hold"
    PLAY = "play"
    NO_SAVING_PLAN = "no_saving_plan"


class PersonalOutcome(Enum):
    NOT_SPECIFIED = "not_specified"
    YOU_GO_HOME = "you_go_home"
    ALLY_GOES_HOME = "ally_goes_home"
    ALLIANCE_SAFE = "alliance_safe"


@dataclass
class Ballot(Output):
    voter: Annotated[str, "An attending contestant, casting exactly one vote"]
    target: Annotated[str, "Another attending contestant"]


@dataclass
class VoteRules(Output):
    tie_rule: Annotated[TieRule, "priority, revote_priority, or revote_rocks; exact rules in README"]
    priority_order: Annotated[
        list[str], "Every contestant once; first eligible name loses a deadlock. Ask if missing; never invent an order."
    ]


@dataclass
class CouncilInput(Output):
    contestants: Annotated[
        list[str],
        "2 to 24 unique, case-sensitive names, in display order; extract the roster from the user's description",
    ]
    alliance: Annotated[list[str], "Nonempty subset; survival means every listed member remains"]
    votes: Annotated[
        list[Ballot],
        "Exactly one assumed ordinary ballot per contestant, before blocks and extra votes. Expand grouped prose; "
        "ask for missing ballots. These are scenario assumptions, not predictions of actual votes.",
    ]
    challenge_immune: Annotated[list[str], "Contestants who cannot receive any ballot; [] when the user says nobody"]
    idol_protected: Annotated[
        list[str], "Idols already played: protected recipients. Held, unplayed idols belong in the planner inventory."
    ]
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


@dataclass
class VoteChange(Output):
    voter: str
    from_target: str
    to_target: str
    outcome: CouncilOutput


@dataclass
class RescueOutput(Output):
    council: Annotated[CouncilInput, "The interpreted input: check that these facts match your written scenario"]
    baseline: Annotated[CouncilOutput, "The council outcome before any changes"]
    status: Annotated[RescueStatus, "already_safe, rescuable, or impossible under the single-vote search rules"]
    tested_changes: Annotated[int, "Number of legal one-vote alternatives checked; zero when already safe"]
    saving_change_count: Annotated[int, "Total alternatives that keep every alliance member safe"]
    suggestions: Annotated[
        list[VoteChange], "First five saving changes in roster voter/target order, with complete verified outcomes"
    ]


@dataclass
class AdvantageItem(Output):
    id: Annotated[str, "Unique item label, 1 to 40 printable trimmed characters; each item is single-use"]
    owner: Annotated[str, "An alliance member who controls this usable item"]
    kind: Annotated[
        AdvantageKind,
        "idol nullifies ordinary and extra votes against its recipient; extra_vote adds one ballot even if its owner's "
        "ordinary ballot is blocked; vote_block removes only the target's ordinary ballot, once.",
    ]
    allowed_targets: Annotated[
        list[str],
        "Legal targets to compare, honoring stated restrictions. Normal idols: anyone; extra votes: legal vote targets; "
        "vote blocks: anyone except the owner. Challenge immunity does not prevent a player's vote being blocked.",
    ]


@dataclass
class AdvantageInput(Output):
    council: Annotated[CouncilInput, "Known intended ordinary ballots before optional plays; priority ties, no revotes"]
    inventory: Annotated[
        list[AdvantageItem],
        "0 to 3 usable alliance-owned items. Ask what is available; never invent an item or a restriction.",
    ]


@dataclass
class AdvantagePlay(Output):
    item_id: str
    target: str


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
class ScenarioInput(Output):
    council: Annotated[
        CouncilInput,
        "Complete assumed ordinary votes and tie rules. Keep idol_protected empty: list every played idol in plays.",
    ]
    plays: Annotated[
        list[PlayedAdvantage],
        "All 0 to 24 items assumed PLAYED in this scenario, including opponents' plays. Held items have no effect. "
        "Use [] when the user explicitly says no items are played; never invent a play from ownership.",
    ]
    perspective: Annotated[
        str | None,
        "The user's contestant name, which must be in the alliance; null if they have not identified themselves. "
        "Never guess which named contestant 'I' means.",
    ]


@dataclass
class ScenarioOutput(Output):
    scenario: Annotated[ScenarioInput, "Echo of the assumed facts, for checking the chat model's interpretation"]
    outcome: Annotated[CouncilOutput, "Calculated outcome conditional on exactly these votes, plays, and rules"]
    personal_outcome: PersonalOutcome
    idol_recipients: Annotated[list[str], "Protected recipients in roster order; ownership alone gives no protection"]
    blocked_voters: Annotated[list[str], "Voters whose ordinary initial ballot was removed, in roster order"]
    extra_votes: Annotated[list[Ballot], "Added ballots in supplied play order, including idol-nullified extra votes"]


@dataclass
class AdvantagePlan(Output):
    plays: list[AdvantagePlay]
    outcome: Annotated[
        CouncilOutput | None, "Full weighted vote outcome, or null when a play leaves no vulnerable contestant"
    ]
    reason: Annotated[str, "Empty for a valid plan; explains an invalid plan"]


@dataclass
class PlayComparison(Output):
    play: AdvantagePlay
    owner: str
    kind: AdvantageKind
    eliminated: str | None
    alliance_survives: bool | None
    nullified_votes: int | None
    vote_tally: Annotated[
        list[VoteCount], "Every contestant's counted votes after this play; empty for an invalid play"
    ]
    reason: str


@dataclass
class AdvantageOutput(Output):
    scenario: Annotated[AdvantageInput, "The council and inventory interpreted from the user's description"]
    baseline: Annotated[CouncilOutput, "Outcome if none of the optional inventory items are played"]
    decision: Annotated[AdvantageDecision, "hold, play, or no_saving_plan with up to two items"]
    minimum_items_needed: Annotated[int | None, "0, 1, or 2; null means no saving plan within the two-item search"]
    plans_checked: Annotated[int, "Includes no play, every legal single play, and every legal two-item combination"]
    saving_plan_count: Annotated[int, "All valid plans keeping the entire alliance safe, including no play if safe"]
    minimal_saving_plan_count: Annotated[int, "Number of saving plans using the fewest items"]
    recommendations: Annotated[
        list[AdvantagePlan], "First five minimum-item saving plans in canonical inventory/roster order"
    ]
    single_plays: Annotated[
        list[PlayComparison], "Every single-item option, including wasteful, harmful, and invalid plays"
    ]


TOOLS = {
    Tool.EVALUATE_SCENARIO: (ScenarioInput, ScenarioOutput),
    Tool.RESOLVE_VOTE: (CouncilInput, CouncilOutput),
    Tool.FIND_RESCUE: (CouncilInput, RescueOutput),
    Tool.PLAN_ADVANTAGES: (AdvantageInput, AdvantageOutput),
}
TASKS = {
    Task.SCENARIO_OUTCOME: (ScenarioInput, ScenarioOutput),
    Task.ALLIANCE_SURVIVAL: (CouncilInput, CouncilOutput),
    Task.SINGLE_VOTE_RESCUE: (CouncilInput, RescueOutput),
    Task.ADVANTAGE_PLANNER: (AdvantageInput, AdvantageOutput),
}
