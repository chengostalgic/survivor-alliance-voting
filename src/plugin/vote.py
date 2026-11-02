"""Tool implementation; the verifier independently reconstructs the result."""

from collections import Counter
from pathlib import Path

from contract import CouncilInput, CouncilOutput, Resolution, TieRule, VoteCount


def check_ballots(ballots, voters, targets):
    if Counter(ballot.voter for ballot in ballots) != Counter(voters):
        raise ValueError("ballots must include exactly one vote from each eligible voter")
    for ballot in ballots:
        if ballot.target not in targets:
            raise ValueError("ballot targets must be eligible contestants")
        if ballot.target == ballot.voter:
            raise ValueError("self votes are forbidden")


def leaders(counts, eligible):
    maximum = max(counts[name] for name in eligible)
    return [name for name in eligible if counts[name] == maximum]


def resolve_vote(council: CouncilInput, workspace: Path) -> CouncilOutput:
    """Resolve one council without network access, randomness, or file writes."""
    return resolve_effective_vote(council, council.votes)


def resolve_effective_vote(council: CouncilInput, effective_ballots) -> CouncilOutput:
    """Validate intended ordinary votes, then count a caller's explicit post-advantage ballots."""
    names = council.contestants
    if not 2 <= len(names) <= 24 or len(set(names)) != len(names):
        raise ValueError("contestants must contain 2 to 24 unique names")
    if any(not name or name != name.strip() or len(name) > 80 or not name.isprintable() for name in names):
        raise ValueError("names must be printable, trimmed, and 1 to 80 characters")
    for group in (council.alliance, council.challenge_immune, council.idol_protected):
        if len(set(group)) != len(group) or not set(group) <= set(names):
            raise ValueError("alliance and immunity lists must be unique subsets of contestants")
    if not council.alliance:
        raise ValueError("alliance must not be empty")
    if Counter(council.rules.priority_order) != Counter(names):
        raise ValueError("priority_order must contain every contestant exactly once")

    protected = set(council.challenge_immune) | set(council.idol_protected)
    vulnerable = [name for name in names if name not in protected]
    if not vulnerable:
        raise ValueError("at least one contestant must be vulnerable")
    check_ballots(council.votes, names, set(names) - set(council.challenge_immune))
    counts = Counter({name: 0 for name in names})
    nullified = 0
    for ballot in effective_ballots:
        if ballot.target in council.idol_protected:
            nullified += 1
        else:
            counts[ballot.target] += 1
    tied = leaders(counts, vulnerable)
    candidates = tied
    revote_counts = None
    resolution = Resolution.INITIAL_VOTE
    if len(tied) == 1:
        if council.revotes:
            raise ValueError("revotes must be empty when the initial vote has a unique leader")
    elif council.rules.tie_rule == TieRule.PRIORITY:
        if council.revotes:
            raise ValueError("revotes must be empty for the priority tie rule")
        resolution = Resolution.PRIORITY
    else:
        voters = [name for name in names if name not in tied]
        check_ballots(council.revotes, voters, set(tied))
        revote_counts = Counter({name: 0 for name in names})
        revote_counts.update(ballot.target for ballot in council.revotes)
        candidates = leaders(revote_counts, tied)
        if len(candidates) == 1:
            resolution = Resolution.REVOTE
        elif council.rules.tie_rule == TieRule.REVOTE_PRIORITY:
            resolution = Resolution.PRIORITY
        else:
            candidates = [name for name in vulnerable if name not in tied]
            if not candidates:
                raise ValueError("rock deadlock has no eligible rock drawers")
            resolution = Resolution.ROCKS

    eliminated = next(name for name in council.rules.priority_order if name in candidates)
    return CouncilOutput(
        eliminated=eliminated,
        alliance_survives=eliminated not in council.alliance,
        alliance_remaining=[name for name in names if name in council.alliance and name != eliminated],
        initial_tally=[VoteCount(name, counts[name]) for name in names],
        nullified_votes=nullified,
        revote_tally=[] if revote_counts is None else [VoteCount(name, revote_counts[name]) for name in names],
        resolution=resolution,
        deciding_candidates=candidates,
    )
