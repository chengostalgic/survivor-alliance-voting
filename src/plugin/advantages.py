"""Compare spending zero, one, or two available advantages against known ballots."""

from collections import Counter
from pathlib import Path

from contract import (
    AdvantageDecision,
    AdvantageInput,
    AdvantageKind,
    AdvantageOutput,
    AdvantagePlan,
    AdvantagePlay,
    CouncilOutput,
    PlayComparison,
    Resolution,
    TieRule,
    VoteCount,
)

from .vote import resolve_vote


def validate_inventory(value):
    if len(value.inventory) > 3:
        raise ValueError("inventory may contain at most three usable items")
    ids = [item.id for item in value.inventory]
    if len(set(ids)) != len(ids):
        raise ValueError("inventory item ids must be unique")
    for item in value.inventory:
        if not item.id or item.id != item.id.strip() or len(item.id) > 40 or not item.id.isprintable():
            raise ValueError("item ids must be printable, trimmed, and 1 to 40 characters")
        if item.owner not in value.council.alliance:
            raise ValueError("only alliance-owned items can be planned")
        targets = item.allowed_targets
        if not targets or len(targets) != len(set(targets)) or not set(targets) <= set(value.council.contestants):
            raise ValueError("allowed_targets must be a nonempty unique subset of the roster")
        if item.kind != AdvantageKind.IDOL and item.owner in targets:
            raise ValueError("extra votes and vote blocks cannot target their owner")
        if item.kind == AdvantageKind.EXTRA_VOTE and set(targets) & set(value.council.challenge_immune):
            raise ValueError("extra votes cannot target challenge-immune contestants")


def candidate_plays(value):
    choices = [
        [AdvantagePlay(item.id, name) for name in value.council.contestants if name in item.allowed_targets]
        for item in value.inventory
    ]
    yield []
    for options in choices:
        for play in options:
            yield [play]
    for first, options in enumerate(choices):
        for second in range(first + 1, len(choices)):
            for left in options:
                for right in choices[second]:
                    yield [left, right]


def evaluate_plan(value, plays):
    council = value.council
    inventory = {item.id: item for item in value.inventory}
    blocked = set()
    protected = set(council.idol_protected)
    extra_targets = []
    for play in plays:
        item = inventory[play.item_id]
        if item.kind == AdvantageKind.IDOL:
            protected.add(play.target)
        elif item.kind == AdvantageKind.VOTE_BLOCK:
            blocked.add(play.target)
        else:
            extra_targets.append(play.target)
    targets = [ballot.target for ballot in council.votes if ballot.voter not in blocked] + extra_targets
    vulnerable = [
        name for name in council.contestants if name not in protected and name not in council.challenge_immune
    ]
    if not vulnerable:
        return AdvantagePlan(plays, None, "no vulnerable contestant remains after these plays")
    counts = Counter(target for target in targets if target not in protected)
    maximum = max(counts[name] for name in vulnerable)
    tied = [name for name in vulnerable if counts[name] == maximum]
    loser = next(name for name in council.rules.priority_order if name in tied)
    outcome = CouncilOutput(
        eliminated=loser,
        alliance_survives=loser not in council.alliance,
        alliance_remaining=[name for name in council.contestants if name in council.alliance and name != loser],
        initial_tally=[VoteCount(name, counts[name]) for name in council.contestants],
        nullified_votes=sum(target in protected for target in targets),
        revote_tally=[],
        resolution=Resolution.PRIORITY if len(tied) > 1 else Resolution.INITIAL_VOTE,
        deciding_candidates=tied,
    )
    return AdvantagePlan(plays, outcome, "")


def plan_advantages(value: AdvantageInput, workspace: Path) -> AdvantageOutput:
    if value.council.rules.tie_rule != TieRule.PRIORITY:
        raise ValueError("advantage planning requires priority ties and an explicit priority_order")
    baseline = resolve_vote(value.council, workspace)
    validate_inventory(value)
    inventory = {item.id: item for item in value.inventory}
    checked = 0
    saving = 0
    minimum = None
    cheapest_count = 0
    recommendations = []
    comparisons = []
    for plays in candidate_plays(value):
        plan = evaluate_plan(value, plays)
        checked += 1
        if len(plays) == 1:
            item = inventory[plays[0].item_id]
            comparisons.append(
                PlayComparison(
                    plays[0],
                    item.owner,
                    item.kind,
                    None if plan.outcome is None else plan.outcome.eliminated,
                    None if plan.outcome is None else plan.outcome.alliance_survives,
                    None if plan.outcome is None else plan.outcome.nullified_votes,
                    [] if plan.outcome is None else plan.outcome.initial_tally,
                    plan.reason,
                )
            )
        if plan.outcome is not None and plan.outcome.alliance_survives:
            saving += 1
            spent = len(plays)
            if minimum is None or spent < minimum:
                minimum, cheapest_count, recommendations = spent, 1, [plan]
            elif spent == minimum:
                cheapest_count += 1
                if len(recommendations) < 5:
                    recommendations.append(plan)
    decision = AdvantageDecision.NO_SAVING_PLAN
    if minimum == 0:
        decision = AdvantageDecision.HOLD
    elif minimum is not None:
        decision = AdvantageDecision.PLAY
    return AdvantageOutput(
        value,
        baseline,
        decision,
        minimum,
        checked,
        saving,
        cheapest_count,
        recommendations,
        comparisons,
    )
