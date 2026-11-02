"""Ballot validation and tally helpers."""

from collections import Counter


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
