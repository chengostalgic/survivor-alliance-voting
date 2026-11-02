"""Independent oracle: count ballots by scanning each candidate's votes.

Only the declarative contract is shared with the runtime. No runtime solver,
network, model, environment, clock, random source, or workspace files are used.
"""

from contract import CouncilOutput, Resolution, TieRule, VoteCount


def verdict(valid, message, **details):
    return {"valid": valid, "score": 1.0 if valid else 0.0, "message": message, "details": details}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def audit_ballots(ballots, voters, targets):
    require(len(ballots) == len(voters), "wrong number of ballots")
    require({ballot.voter for ballot in ballots} == set(voters), "missing, duplicate, or ineligible voter")
    require(all(ballot.target in targets for ballot in ballots), "ineligible ballot target")
    require(all(ballot.voter != ballot.target for ballot in ballots), "self votes are forbidden")


def reconstruct(value):
    """Return the unique expected typed result; reject semantically invalid inputs."""
    order = value.contestants
    roster = set(order)
    require(2 <= len(order) <= 24 and len(roster) == len(order), "expected 2 to 24 unique contestants")
    require(
        all(name and name.strip() == name and len(name) <= 80 and name.isprintable() for name in order),
        "contestant names must be printable, trimmed, and 1 to 80 characters",
    )
    for members in (value.alliance, value.challenge_immune, value.idol_protected):
        require(len(members) == len(set(members)) and set(members) <= roster, "invalid alliance or immunity list")
    require(bool(value.alliance), "alliance must not be empty")
    priority = value.rules.priority_order
    require(len(priority) == len(order) and set(priority) == roster, "priority_order must be a roster permutation")
    safe = set(value.challenge_immune + value.idol_protected)
    eligible = [name for name in order if name not in safe]
    require(bool(eligible), "no vulnerable contestants")
    audit_ballots(value.votes, order, roster - set(value.challenge_immune))

    initial = [
        VoteCount(name, sum(ballot.target == name and name not in safe for ballot in value.votes)) for name in order
    ]
    highest = max(row.votes for row in initial if row.contestant in eligible)
    initial_tied = [row.contestant for row in initial if row.contestant in eligible and row.votes == highest]
    final_candidates = initial_tied
    second = []
    method = Resolution.INITIAL_VOTE
    if len(initial_tied) > 1 and value.rules.tie_rule != TieRule.PRIORITY:
        audit_ballots(value.revotes, [name for name in order if name not in initial_tied], set(initial_tied))
        second = [VoteCount(name, sum(ballot.target == name for ballot in value.revotes)) for name in order]
        highest = max(row.votes for row in second if row.contestant in initial_tied)
        final_candidates = [row.contestant for row in second if row.contestant in initial_tied and row.votes == highest]
        method = Resolution.REVOTE
        if len(final_candidates) > 1:
            method = Resolution.PRIORITY
            if value.rules.tie_rule == TieRule.REVOTE_ROCKS:
                final_candidates = [name for name in eligible if name not in initial_tied]
                require(bool(final_candidates), "rock deadlock has no eligible rock drawers")
                method = Resolution.ROCKS
    else:
        require(not value.revotes, "unexpected revote ballots")
        if len(initial_tied) > 1:
            method = Resolution.PRIORITY

    loser = min(final_candidates, key=priority.index)
    return CouncilOutput(
        eliminated=loser,
        alliance_survives=all(member != loser for member in value.alliance),
        alliance_remaining=[name for name in order if name in value.alliance and name != loser],
        initial_tally=initial,
        nullified_votes=sum(ballot.target in value.idol_protected for ballot in value.votes),
        revote_tally=second,
        resolution=method,
        deciding_candidates=final_candidates,
    )


def check_input(value):
    try:
        reconstruct(value)
    except ValueError as error:
        return verdict(False, str(error))
    return verdict(True, "council input obeys the declared rules")


def check_result(value, output):
    try:
        expected = reconstruct(value)
    except ValueError as error:
        return verdict(False, "invalid council: " + str(error))
    if output != expected:
        return verdict(False, "result does not match the ballots and rules", expected=expected)
    return verdict(
        True,
        "council outcome and alliance survival are correct",
        eliminated=expected.eliminated,
        alliance_survives=expected.alliance_survives,
    )
