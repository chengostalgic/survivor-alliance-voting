"""Independently audit explicit plays, rebuild cast ballots, and verify the conditional outcome."""

from dataclasses import replace

from contract import AdvantageKind, Ballot, PersonalOutcome, ScenarioOutput

from .vote import reconstruct, require, verdict


def reconstruct_scenario(value):
    source = value.council
    require(not source.idol_protected, "played idols must be explicit plays, not implicit protection")
    require(value.perspective is None or value.perspective in source.alliance, "invalid perspective")
    require(len(value.plays) <= 24, "too many played items")
    ids = [play.id for play in value.plays]
    require(len(set(ids)) == len(ids), "an item cannot be reused")
    for play in value.plays:
        require(
            bool(play.id) and len(play.id) <= 40 and play.id == play.id.strip() and play.id.isprintable(),
            "invalid item id",
        )
        require(play.owner in source.contestants and play.target in source.contestants, "unknown owner or target")
        if play.kind != AdvantageKind.IDOL:
            require(play.owner != play.target, "self-targeted extra vote or vote block")
        if play.kind == AdvantageKind.EXTRA_VOTE:
            require(play.target not in source.challenge_immune, "extra vote targets challenge immunity")

    recipients = [
        name
        for name in source.contestants
        if any(play.kind == AdvantageKind.IDOL and play.target == name for play in value.plays)
    ]
    removed = [
        name
        for name in source.contestants
        if any(play.kind == AdvantageKind.VOTE_BLOCK and play.target == name for play in value.plays)
    ]
    added = [Ballot(play.owner, play.target) for play in value.plays if play.kind == AdvantageKind.EXTRA_VOTE]
    cast = [ballot for ballot in source.votes if ballot.voter not in removed] + added
    calculated = reconstruct(replace(source, idol_protected=recipients), initial_ballots=cast)
    if value.perspective is None:
        personal = PersonalOutcome.NOT_SPECIFIED
    elif calculated.eliminated == value.perspective:
        personal = PersonalOutcome.YOU_GO_HOME
    elif calculated.eliminated in source.alliance:
        personal = PersonalOutcome.ALLY_GOES_HOME
    else:
        personal = PersonalOutcome.ALLIANCE_SAFE
    return ScenarioOutput(value, calculated, personal, recipients, removed, added)


def check_input(value):
    try:
        reconstruct_scenario(value)
    except ValueError as error:
        return verdict(False, str(error))
    return verdict(True, "complete assumed council and explicit plays obey the declared rules")


def check_result(value, output):
    try:
        expected = reconstruct_scenario(value)
    except ValueError as error:
        return verdict(False, "invalid assumed scenario: " + str(error))
    if output != expected:
        return verdict(
            False, "outcome differs from the assumed votes, explicit plays, or perspective", expected=expected
        )
    return verdict(
        True,
        "calculation is correct conditional on the supplied assumptions",
        eliminated=expected.outcome.eliminated,
        personal_outcome=expected.personal_outcome,
        alliance_survives=expected.outcome.alliance_survives,
    )
