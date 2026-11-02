"""Vote/revote/deadlock/rocks and explicit final-four formats, without ordered tiebreaks."""

from collections import Counter
from pathlib import Path

from contract import (
    AdvantageKind,
    Ballot,
    CouncilFormat,
    CouncilStage,
    NeededFact,
    PersonalOutcome,
    Resolution,
    ResolutionFacts,
    TribalOutcome,
    TribalScenarioInput,
    TribalScenarioOutput,
    VoteCount,
)

from .vote import check_ballots, leaders


def resolve_tribal(value: TribalScenarioInput, workspace: Path) -> TribalScenarioOutput:
    council = value.council
    names = council.contestants
    roster = set(names)
    if not 2 <= len(names) <= 24 or len(roster) != len(names):
        raise ValueError("contestants must contain 2 to 24 unique names")
    if any(not name or name.strip() != name or len(name) > 80 or not name.isprintable() for name in names):
        raise ValueError("names must be printable, trimmed, and 1 to 80 characters")
    for group in (council.alliance, council.challenge_immune):
        if len(group) != len(set(group)) or not set(group) <= roster:
            raise ValueError("alliance and immunity must be unique roster subsets")
    if not council.alliance or (value.perspective is not None and value.perspective not in council.alliance):
        raise ValueError("supply a nonempty alliance and an allied perspective or null")
    mode = council.format or CouncilFormat.STANDARD
    if mode != CouncilFormat.STANDARD and len(names) != 4:
        raise ValueError("a final-four format requires exactly four contestants")
    facts = value.resolution_facts or ResolutionFacts(None, None, [], None)
    has_facts = any(
        name is not None for name in (facts.consensus_eliminated, facts.rock_draw_loser, facts.fire_winner)
    ) or bool(facts.fire_participants)
    if mode != CouncilFormat.STANDARD and value.plays:
        raise ValueError("the supported final-four formats do not allow advantage plays")
    for name in (facts.consensus_eliminated, facts.rock_draw_loser, facts.fire_winner):
        if name is not None and name not in roster:
            raise ValueError("unknown resolution contestant")
    if facts.consensus_eliminated is not None and facts.rock_draw_loser is not None:
        raise ValueError("a unanimous decision and rock result cannot both resolve this council")
    if facts.fire_participants and (
        len(facts.fire_participants) != 2
        or len(set(facts.fire_participants)) != 2
        or not set(facts.fire_participants) <= roster
    ):
        raise ValueError("fire_participants must be two different contestants, or [] when unknown")

    protected, blocked, extra, used = set(), set(), [], set()
    if len(value.plays) > 24:
        raise ValueError("at most 24 played items are supported")
    for play in value.plays:
        if (
            not play.id
            or play.id.strip() != play.id
            or len(play.id) > 40
            or not play.id.isprintable()
            or play.id in used
        ):
            raise ValueError("played item IDs must be unique, printable, trimmed, and 1 to 40 characters")
        used.add(play.id)
        if play.owner not in roster or play.target not in roster:
            raise ValueError("unknown played item owner or target")
        if play.kind == AdvantageKind.IDOL:
            protected.add(play.target)
        else:
            if play.owner == play.target:
                raise ValueError("extra votes and vote blocks cannot target their owner")
            if play.kind == AdvantageKind.VOTE_BLOCK:
                blocked.add(play.target)
            else:
                if play.target in council.challenge_immune:
                    raise ValueError("extra votes cannot target challenge immunity")
                extra.append(Ballot(play.owner, play.target))

    initial, second, tied, voters, drawers, fire = [], [], [], [], [], []
    nullified = 0

    def result(stage, loser=None, method=None, needed=()):
        outcome = TribalOutcome(
            stage,
            loser,
            None if loser is None else loser not in council.alliance,
            None if loser is None else [name for name in names if name in council.alliance and name != loser],
            initial,
            nullified,
            second,
            method,
            tied,
            voters,
            drawers,
            fire,
            list(needed),
        )
        personal = PersonalOutcome.NOT_SPECIFIED
        if value.perspective is not None:
            personal = (
                PersonalOutcome.AWAITING_RESULT
                if loser is None
                else (
                    PersonalOutcome.YOU_GO_HOME
                    if loser == value.perspective
                    else PersonalOutcome.ALLY_GOES_HOME
                    if loser in council.alliance
                    else PersonalOutcome.ALLIANCE_SAFE
                )
            )
        return TribalScenarioOutput(
            value,
            outcome,
            personal,
            [name for name in names if name in protected],
            [name for name in names if name in blocked],
            extra,
        )

    def finish_fire():
        if facts.consensus_eliminated is not None or facts.rock_draw_loser is not None:
            raise ValueError("this fire-making format is not resolved by consensus or rocks")
        if not fire:
            if facts.fire_winner is not None:
                raise ValueError("specify both fire participants before naming a winner")
            return result(CouncilStage.FIRE_REQUIRED, needed=[NeededFact.FIRE_PAIR, NeededFact.FIRE_WINNER])
        if facts.fire_winner is None:
            return result(CouncilStage.FIRE_REQUIRED, needed=[NeededFact.FIRE_WINNER])
        if facts.fire_winner not in fire:
            raise ValueError("fire_winner must be one of the fire contestants")
        loser = next(name for name in fire if name != facts.fire_winner)
        return result(CouncilStage.COMPLETE, loser, Resolution.FIRE)

    if mode == CouncilFormat.FINAL_FOUR_FIRE:
        if council.votes or council.revotes or value.plays:
            raise ValueError("forced final-four fire has no votes, revotes, or advantage plays in this model")
        fire = [name for name in names if name in facts.fire_participants]
        if set(fire) & set(council.challenge_immune):
            raise ValueError("a contestant protected by immunity cannot be in the stated fire pair")
        return finish_fire()

    check_ballots(council.votes, names, roster - set(council.challenge_immune))
    vulnerable = [name for name in names if name not in protected and name not in council.challenge_immune]
    if not vulnerable:
        raise ValueError("at least one contestant must remain vulnerable")
    cast = [ballot for ballot in council.votes if ballot.voter not in blocked] + extra
    counts = Counter(ballot.target for ballot in cast if ballot.target not in protected)
    nullified = sum(ballot.target in protected for ballot in cast)
    initial = [VoteCount(name, counts[name]) for name in names]
    candidates = leaders(counts, vulnerable)
    if len(candidates) == 1:
        if council.revotes or has_facts:
            raise ValueError("a unique initial leader needs no revotes or resolution facts")
        return result(CouncilStage.COMPLETE, candidates[0], Resolution.INITIAL_VOTE)

    tied = candidates
    voters = [name for name in names if name not in tied]
    if voters and not council.revotes:
        return result(CouncilStage.REVOTE_REQUIRED, needed=[NeededFact.REVOTES])
    check_ballots(council.revotes, voters, set(tied))
    revote_counts = Counter(ballot.target for ballot in council.revotes)
    second = [VoteCount(name, revote_counts[name]) for name in names]
    candidates = leaders(revote_counts, tied)
    if len(candidates) == 1:
        if has_facts:
            raise ValueError("a unique revote leader needs no deadlock resolution facts")
        return result(CouncilStage.COMPLETE, candidates[0], Resolution.REVOTE)

    if mode == CouncilFormat.FINAL_FOUR_VOTE:
        if len(candidates) != 2:
            raise ValueError("the supported final-four voting deadlock requires two fire contestants")
        fire = candidates
        if facts.fire_participants and set(facts.fire_participants) != set(fire):
            raise ValueError("the deadlocked contestants must be the fire participants")
        return finish_fire()

    if facts.fire_participants or facts.fire_winner is not None:
        raise ValueError("standard deadlocks use unanimous agreement or rocks; specify a final-four format for fire")
    drawers = [name for name in vulnerable if name not in tied]
    if facts.consensus_eliminated is not None:
        if facts.consensus_eliminated not in candidates:
            raise ValueError("the unanimous decision must select a contestant still tied after the revote")
        return result(CouncilStage.COMPLETE, facts.consensus_eliminated, Resolution.CONSENSUS)
    if facts.rock_draw_loser is not None:
        if facts.rock_draw_loser not in drawers:
            raise ValueError("the stated rock loser must be an eligible non-tied, non-protected drawer")
        return result(CouncilStage.COMPLETE, facts.rock_draw_loser, Resolution.ROCKS)
    return result(CouncilStage.DEADLOCK, needed=[NeededFact.DEADLOCK_RESULT])
