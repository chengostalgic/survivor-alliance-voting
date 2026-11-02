"""Independent per-candidate replay of standard council stages and supplied fire/rock results."""

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
    TribalScenarioOutput,
    VoteCount,
)

from .vote import audit_ballots, require, verdict


def reconstruct_tribal(value):
    council = value.council
    names, allies, immune = council.contestants, council.alliance, council.challenge_immune
    roster = set(names)
    require(2 <= len(names) <= 24 and len(names) == len(roster), "expected 2 to 24 unique contestants")
    require(
        all(name and name == name.strip() and len(name) <= 80 and name.isprintable() for name in names),
        "invalid contestant name",
    )
    for group in (allies, immune):
        require(len(group) == len(set(group)) and set(group) <= roster, "invalid alliance or immunity list")
    require(bool(allies), "empty alliance")
    require(value.perspective is None or value.perspective in allies, "invalid personal perspective")
    mode = CouncilFormat.STANDARD if council.format is None else council.format
    require(mode == CouncilFormat.STANDARD or len(names) == 4, "final-four format requires four contestants")
    facts = value.resolution_facts if value.resolution_facts is not None else ResolutionFacts(None, None, [], None)
    known = [facts.consensus_eliminated, facts.rock_draw_loser, facts.fire_winner]
    require(all(name is None or name in roster for name in known), "unknown resolution contestant")
    require(facts.consensus_eliminated is None or facts.rock_draw_loser is None, "contradictory deadlock resolutions")
    require(
        not facts.fire_participants
        or (
            len(facts.fire_participants) == 2
            and len(set(facts.fire_participants)) == 2
            and set(facts.fire_participants) <= roster
        ),
        "invalid fire participants",
    )
    has_facts = any(name is not None for name in known) or bool(facts.fire_participants)
    require(mode == CouncilFormat.STANDARD or not value.plays, "final-four formats do not support advantage plays")
    require(len(value.plays) <= 24, "too many played items")
    labels = [play.id for play in value.plays]
    require(len(set(labels)) == len(labels), "reused played item")
    for play in value.plays:
        require(
            bool(play.id) and len(play.id) <= 40 and play.id == play.id.strip() and play.id.isprintable(),
            "invalid item id",
        )
        require(play.owner in roster and play.target in roster, "unknown play owner or target")
        if play.kind != AdvantageKind.IDOL:
            require(play.owner != play.target, "self-targeted vote advantage")
        if play.kind == AdvantageKind.EXTRA_VOTE:
            require(play.target not in immune, "extra vote targets immunity")
    protected = [
        name for name in names if any(play.kind == AdvantageKind.IDOL and play.target == name for play in value.plays)
    ]
    blocked = [
        name
        for name in names
        if any(play.kind == AdvantageKind.VOTE_BLOCK and play.target == name for play in value.plays)
    ]
    added = [Ballot(play.owner, play.target) for play in value.plays if play.kind == AdvantageKind.EXTRA_VOTE]
    first, second, original_tie, voters, drawers, fire = [], [], [], [], [], []
    nullified = 0

    def finish(stage, loser=None, method=None, needs=()):
        personal = PersonalOutcome.NOT_SPECIFIED
        if value.perspective is not None:
            personal = PersonalOutcome.AWAITING_RESULT
            if loser is not None:
                personal = PersonalOutcome.ALLIANCE_SAFE
                if loser in allies:
                    personal = (
                        PersonalOutcome.YOU_GO_HOME if loser == value.perspective else PersonalOutcome.ALLY_GOES_HOME
                    )
        result = TribalOutcome(
            stage,
            loser,
            None if loser is None else loser not in allies,
            None if loser is None else [name for name in names if name in allies and name != loser],
            first,
            nullified,
            second,
            method,
            original_tie,
            voters,
            drawers,
            fire,
            list(needs),
        )
        return TribalScenarioOutput(value, result, personal, protected, blocked, added)

    def fire_result():
        require(
            facts.consensus_eliminated is None and facts.rock_draw_loser is None,
            "fire cannot be resolved by consensus or rocks",
        )
        if not fire:
            require(facts.fire_winner is None, "fire winner supplied without participants")
            return finish(CouncilStage.FIRE_REQUIRED, needs=[NeededFact.FIRE_PAIR, NeededFact.FIRE_WINNER])
        if facts.fire_winner is None:
            return finish(CouncilStage.FIRE_REQUIRED, needs=[NeededFact.FIRE_WINNER])
        require(facts.fire_winner in fire, "winner is not a fire participant")
        return finish(CouncilStage.COMPLETE, next(name for name in fire if name != facts.fire_winner), Resolution.FIRE)

    if mode == CouncilFormat.FINAL_FOUR_FIRE:
        require(not council.votes and not council.revotes, "forced fire has no ballots")
        fire = [name for name in names if name in facts.fire_participants]
        require(not set(fire) & set(immune), "immune contestant cannot make fire")
        return fire_result()

    audit_ballots(council.votes, names, roster - set(immune))
    vulnerable = [name for name in names if name not in immune and name not in protected]
    require(bool(vulnerable), "no vulnerable contestants")
    cast = [ballot for ballot in council.votes if ballot.voter not in blocked] + added
    first = [
        VoteCount(name, sum(ballot.target == name for ballot in cast) if name not in protected else 0) for name in names
    ]
    nullified = sum(ballot.target in protected for ballot in cast)
    highest = max(row.votes for row in first if row.contestant in vulnerable)
    candidates = [row.contestant for row in first if row.contestant in vulnerable and row.votes == highest]
    if len(candidates) == 1:
        require(not council.revotes and not has_facts, "unexpected revotes or resolution facts for a unique leader")
        return finish(CouncilStage.COMPLETE, candidates[0], Resolution.INITIAL_VOTE)
    original_tie = candidates
    voters = [name for name in names if name not in original_tie]
    if voters and not council.revotes:
        return finish(CouncilStage.REVOTE_REQUIRED, needs=[NeededFact.REVOTES])
    audit_ballots(council.revotes, voters, set(original_tie))
    second = [VoteCount(name, sum(ballot.target == name for ballot in council.revotes)) for name in names]
    high = max(row.votes for row in second if row.contestant in original_tie)
    remaining_tie = [row.contestant for row in second if row.contestant in original_tie and row.votes == high]
    if len(remaining_tie) == 1:
        require(not has_facts, "unexpected resolution facts for a unique revote leader")
        return finish(CouncilStage.COMPLETE, remaining_tie[0], Resolution.REVOTE)
    if mode == CouncilFormat.FINAL_FOUR_VOTE:
        require(len(remaining_tie) == 2, "supported final-four deadlock needs two fire contestants")
        fire = remaining_tie
        require(
            not facts.fire_participants or set(facts.fire_participants) == set(fire),
            "incorrect fire pair for deadlocked vote",
        )
        return fire_result()
    require(not facts.fire_participants and facts.fire_winner is None, "fire facts supplied for a standard vote")
    drawers = [name for name in vulnerable if name not in original_tie]
    if facts.consensus_eliminated is not None:
        require(facts.consensus_eliminated in remaining_tie, "consensus must eliminate a still-tied contestant")
        return finish(CouncilStage.COMPLETE, facts.consensus_eliminated, Resolution.CONSENSUS)
    if facts.rock_draw_loser is not None:
        require(facts.rock_draw_loser in drawers, "ineligible rock loser")
        return finish(CouncilStage.COMPLETE, facts.rock_draw_loser, Resolution.ROCKS)
    return finish(CouncilStage.DEADLOCK, needs=[NeededFact.DEADLOCK_RESULT])


def check_input(value):
    try:
        reconstruct_tribal(value)
    except ValueError as error:
        return verdict(False, str(error))
    return verdict(True, "scenario follows the supported vote/revote/rocks or final-four format")


def check_result(value, output):
    try:
        expected = reconstruct_tribal(value)
    except ValueError as error:
        return verdict(False, "invalid tribal scenario: " + str(error))
    if output != expected:
        return verdict(
            False, "tribal stage, effects, tally, or outcome differs from the supplied facts", expected=expected
        )
    return verdict(
        True,
        "council stage and conditional result are correct; no random result was invented",
        stage=expected.outcome.stage,
        eliminated=expected.outcome.eliminated,
        alliance_survives=expected.outcome.alliance_survives,
    )
