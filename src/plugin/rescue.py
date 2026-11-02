"""Exhaustively search one initial-vote change by an alliance member."""

from dataclasses import replace
from pathlib import Path

from contract import CouncilInput, RescueOutput, RescueStatus, TieRule, VoteChange

from .vote import resolve_vote

MAX_SUGGESTIONS = 5


def find_rescue(council: CouncilInput, workspace: Path) -> RescueOutput:
    if council.rules.tie_rule != TieRule.PRIORITY:
        raise ValueError("single-vote rescue requires the priority tie rule and an explicit priority_order")
    baseline = resolve_vote(council, workspace)
    if baseline.alliance_survives:
        return RescueOutput(council, baseline, RescueStatus.ALREADY_SAFE, 0, 0, [])

    ballots = {ballot.voter: ballot for ballot in council.votes}
    tested = 0
    saved = 0
    suggestions = []
    for voter in council.contestants:
        if voter not in council.alliance:
            continue
        previous = ballots[voter].target
        for target in council.contestants:
            if target in (voter, previous) or target in council.challenge_immune:
                continue
            changed = replace(
                council,
                votes=[replace(ballot, target=target) if ballot.voter == voter else ballot for ballot in council.votes],
            )
            outcome = resolve_vote(changed, workspace)
            tested += 1
            if outcome.alliance_survives:
                saved += 1
                if len(suggestions) < MAX_SUGGESTIONS:
                    suggestions.append(VoteChange(voter, previous, target, outcome))
    status = RescueStatus.RESCUABLE if saved else RescueStatus.IMPOSSIBLE
    return RescueOutput(council, baseline, status, tested, saved, suggestions)
