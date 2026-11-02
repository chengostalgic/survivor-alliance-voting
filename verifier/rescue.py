"""Independent exhaustive oracle for rescue existence, counts, and suggestions."""

from dataclasses import replace
from itertools import product

from contract import RescueOutput, RescueStatus, TieRule, VoteChange

from .vote import reconstruct, require, verdict


def baseline_for(value):
    require(value.rules.tie_rule == TieRule.PRIORITY, "single-vote rescue requires the priority tie rule")
    return reconstruct(value)


def reconstruct_rescue(value):
    baseline = baseline_for(value)
    if baseline.alliance_survives:
        return RescueOutput(value, baseline, RescueStatus.ALREADY_SAFE, 0, 0, [])

    attempts = 0
    winning = []
    for voter, target in product(value.contestants, repeat=2):
        if voter not in value.alliance or target == voter or target in value.challenge_immune:
            continue
        original = next(ballot.target for ballot in value.votes if ballot.voter == voter)
        if target == original:
            continue
        alternative = replace(
            value,
            votes=[replace(ballot, target=target) if ballot.voter == voter else ballot for ballot in value.votes],
        )
        attempts += 1
        result = reconstruct(alternative)
        if all(member != result.eliminated for member in value.alliance):
            winning.append(VoteChange(voter, original, target, result))
    status = RescueStatus.RESCUABLE if winning else RescueStatus.IMPOSSIBLE
    return RescueOutput(value, baseline, status, attempts, len(winning), winning[:5])


def check_input(value):
    try:
        baseline_for(value)
    except ValueError as error:
        return verdict(False, str(error))
    return verdict(True, "council supports an exhaustive single-vote rescue search")


def check_result(value, output):
    try:
        expected = reconstruct_rescue(value)
    except ValueError as error:
        return verdict(False, "invalid rescue scenario: " + str(error))
    if output != expected:
        return verdict(False, "rescue result does not match the exhaustive search", expected=expected)
    return verdict(
        True,
        "baseline, rescue count, and every suggested vote change are correct",
        status=expected.status,
        tested_changes=expected.tested_changes,
        saving_change_count=expected.saving_change_count,
    )
