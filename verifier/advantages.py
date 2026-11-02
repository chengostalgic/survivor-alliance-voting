"""Independent weighted-ballot oracle and exhaustive zero/one/two-item search."""

from itertools import combinations, product

from contract import (
    AdvantageDecision,
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

from .vote import reconstruct, require, verdict


def validate_scenario(value):
    require(value.council.rules.tie_rule == TieRule.PRIORITY, "advantage planner requires priority ties")
    baseline = reconstruct(value.council)
    require(len(value.inventory) <= 3, "at most three inventory items are supported")
    require(len({item.id for item in value.inventory}) == len(value.inventory), "duplicate inventory item id")
    roster = set(value.council.contestants)
    for item in value.inventory:
        require(
            bool(item.id) and item.id.strip() == item.id and len(item.id) <= 40 and item.id.isprintable(),
            "invalid item id",
        )
        require(item.owner in value.council.alliance, "inventory owner is outside the alliance")
        require(
            bool(item.allowed_targets) and len(set(item.allowed_targets)) == len(item.allowed_targets),
            "invalid target list",
        )
        require(set(item.allowed_targets) <= roster, "unknown advantage target")
        if item.kind in (AdvantageKind.EXTRA_VOTE, AdvantageKind.VOTE_BLOCK):
            require(item.owner not in item.allowed_targets, "an extra vote or vote block cannot target its owner")
        if item.kind == AdvantageKind.EXTRA_VOTE:
            require(
                not set(item.allowed_targets) & set(value.council.challenge_immune),
                "extra vote targets challenge immunity",
            )
    return baseline


def derive_plan(value, plays):
    council = value.council
    uses = [(next(item for item in value.inventory if item.id == play.item_id), play.target) for play in plays]
    blocked = {target for item, target in uses if item.kind == AdvantageKind.VOTE_BLOCK}
    idol_targets = set(council.idol_protected) | {target for item, target in uses if item.kind == AdvantageKind.IDOL}
    remaining = [
        name for name in council.contestants if name not in idol_targets and name not in council.challenge_immune
    ]
    if not remaining:
        return AdvantagePlan(plays, None, "no vulnerable contestant remains after these plays")
    original = [ballot for ballot in council.votes if ballot.voter not in blocked]
    extra = [target for item, target in uses if item.kind == AdvantageKind.EXTRA_VOTE]
    rows = [
        VoteCount(
            name, 0 if name in idol_targets else (sum(ballot.target == name for ballot in original) + extra.count(name))
        )
        for name in council.contestants
    ]
    top = max(row.votes for row in rows if row.contestant in remaining)
    tied = [row.contestant for row in rows if row.contestant in remaining and row.votes == top]
    loser = min(tied, key=council.rules.priority_order.index)
    output = CouncilOutput(
        loser,
        all(member != loser for member in council.alliance),
        [name for name in council.contestants if name in council.alliance and name != loser],
        rows,
        sum(ballot.target in idol_targets for ballot in original) + sum(target in idol_targets for target in extra),
        [],
        Resolution.INITIAL_VOTE if len(tied) == 1 else Resolution.PRIORITY,
        tied,
    )
    return AdvantagePlan(plays, output, "")


def reconstruct_advantages(value):
    baseline = validate_scenario(value)
    plans = []
    singles = []
    for size in range(min(len(value.inventory), 2) + 1):
        for items in combinations(value.inventory, size):
            targets = [[name for name in value.council.contestants if name in item.allowed_targets] for item in items]
            for selection in product(*targets):
                plays = [AdvantagePlay(item.id, target) for item, target in zip(items, selection)]
                plan = derive_plan(value, plays)
                plans.append(plan)
                if size == 1:
                    outcome = plan.outcome
                    singles.append(
                        PlayComparison(
                            plays[0],
                            items[0].owner,
                            items[0].kind,
                            None if outcome is None else outcome.eliminated,
                            None if outcome is None else outcome.alliance_survives,
                            None if outcome is None else outcome.nullified_votes,
                            [] if outcome is None else outcome.initial_tally,
                            plan.reason,
                        )
                    )
    winning = [plan for plan in plans if plan.outcome is not None and plan.outcome.alliance_survives]
    minimum = min((len(plan.plays) for plan in winning), default=None)
    cheapest = [plan for plan in winning if len(plan.plays) == minimum]
    decision = AdvantageDecision.HOLD if minimum == 0 else AdvantageDecision.PLAY
    if minimum is None:
        decision = AdvantageDecision.NO_SAVING_PLAN
    return AdvantageOutput(
        value, baseline, decision, minimum, len(plans), len(winning), len(cheapest), cheapest[:5], singles
    )


def check_input(value):
    try:
        validate_scenario(value)
    except ValueError as error:
        return verdict(False, str(error))
    return verdict(True, "council and usable inventory satisfy the advantage rules")


def check_result(value, output):
    try:
        expected = reconstruct_advantages(value)
    except ValueError as error:
        return verdict(False, "invalid advantage scenario: " + str(error))
    if output != expected:
        return verdict(False, "advantage result does not match the complete search", expected=expected)
    return verdict(
        True,
        "advantage effects, every comparison, and minimum-item plans are correct",
        decision=expected.decision,
        minimum_items_needed=expected.minimum_items_needed,
        plans_checked=expected.plans_checked,
    )
