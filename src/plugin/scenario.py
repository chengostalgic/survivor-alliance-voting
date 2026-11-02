"""Calculate one fully specified hypothetical council; no prediction or play search."""

from dataclasses import replace
from pathlib import Path

from contract import AdvantageKind, Ballot, PersonalOutcome, ScenarioInput, ScenarioOutput

from .vote import resolve_effective_vote


def evaluate_scenario(value: ScenarioInput, workspace: Path) -> ScenarioOutput:
    council = value.council
    if council.idol_protected:
        raise ValueError("scenario-outcome requires every played idol in plays; idol_protected must be empty")
    if value.perspective is not None and value.perspective not in council.alliance:
        raise ValueError("perspective must name an alliance member or be null")
    if len(value.plays) > 24:
        raise ValueError("at most 24 played items are supported")
    used = set()
    protected = set()
    blocked = set()
    extra = []
    for play in value.plays:
        if not play.id or play.id.strip() != play.id or len(play.id) > 40 or not play.id.isprintable():
            raise ValueError("item ids must be printable, trimmed, and 1 to 40 characters")
        if play.id in used:
            raise ValueError("an item may be played only once; duplicate item id")
        used.add(play.id)
        if play.owner not in council.contestants or play.target not in council.contestants:
            raise ValueError("played item owner and target must be contestants")
        if play.kind == AdvantageKind.IDOL:
            protected.add(play.target)
        else:
            if play.target == play.owner:
                raise ValueError("extra votes and vote blocks cannot target their owner")
            if play.kind == AdvantageKind.EXTRA_VOTE:
                if play.target in council.challenge_immune:
                    raise ValueError("extra votes cannot target challenge-immune contestants")
                extra.append(Ballot(play.owner, play.target))
            else:
                blocked.add(play.target)

    recipients = [name for name in council.contestants if name in protected]
    effective = [ballot for ballot in council.votes if ballot.voter not in blocked] + extra
    outcome = resolve_effective_vote(replace(council, idol_protected=recipients), effective)
    personal = PersonalOutcome.NOT_SPECIFIED
    if value.perspective is not None:
        if outcome.eliminated == value.perspective:
            personal = PersonalOutcome.YOU_GO_HOME
        elif outcome.alliance_survives:
            personal = PersonalOutcome.ALLIANCE_SAFE
        else:
            personal = PersonalOutcome.ALLY_GOES_HOME
    return ScenarioOutput(
        value,
        outcome,
        personal,
        recipients,
        [name for name in council.contestants if name in blocked],
        extra,
    )
