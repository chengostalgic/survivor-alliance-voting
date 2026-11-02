"""Standard council stages, explicit final-four formats, and order-independent voting."""

import copy
import itertools
import json
from dataclasses import replace
from pathlib import Path

import pytest
from slimconfig import build_output, output_schema, plain_output

import verifier
from contract import (
    Ballot,
    CouncilFormat,
    CouncilStage,
    PersonalOutcome,
    Resolution,
    ResolutionFacts,
    TribalScenarioInput,
)
from plugin.tribal import resolve_tribal

CASES = Path(__file__).parent / "tribal"


def sample(name="idol-on-other"):
    return build_output(json.loads((CASES / f"{name}.input.json").read_text()), TribalScenarioInput)


@pytest.mark.parametrize("path", sorted(CASES.glob("*.input.json")), ids=lambda path: path.stem)
def test_hand_calculated_standard_scenarios(path, tmp_path):
    given = build_output(json.loads(path.read_text()), TribalScenarioInput)
    before = copy.deepcopy(given)
    expected = json.loads(path.with_name(path.name.replace(".input.", ".expected.")).read_text())
    made = resolve_tribal(given, tmp_path)
    assert plain_output(made) == expected
    assert verifier.verify_input("resolve_tribal", given)["valid"]
    assert verifier.verify_output("resolve_tribal", given, made, "")["valid"]
    assert verifier.verify_task("scenario-outcome", given, made, None, "")["valid"]
    assert given == before and not list(tmp_path.iterdir())


@pytest.mark.parametrize(
    "field", ["scenario", "outcome", "personal_outcome", "idol_recipients", "blocked_voters", "extra_votes"]
)
def test_all_result_fields_are_checked(field, tmp_path):
    given = sample()
    made = resolve_tribal(given, tmp_path)
    changes = {
        "scenario": replace(given, plays=[]),
        "outcome": replace(made.outcome, eliminated="John"),
        "personal_outcome": PersonalOutcome.YOU_GO_HOME,
        "idol_recipients": ["Esther"],
        "blocked_voters": ["Cora"],
        "extra_votes": [Ballot("Esther", "John")],
    }
    assert not verifier.verify_task("scenario-outcome", given, replace(made, **{field: changes[field]}), None, "")[
        "valid"
    ]


@pytest.mark.parametrize(
    "field",
    [
        "stage",
        "eliminated",
        "alliance_survives",
        "alliance_remaining",
        "initial_tally",
        "nullified_votes",
        "revote_tally",
        "resolution",
        "tied_contestants",
        "revote_voters",
        "rock_drawers",
        "fire_contestants",
        "needed_facts",
    ],
)
def test_every_outcome_field_is_checked(field, tmp_path):
    given = sample("deadlock")
    made = resolve_tribal(given, tmp_path)
    changes = {
        "stage": CouncilStage.COMPLETE,
        "eliminated": "Cora",
        "alliance_survives": True,
        "alliance_remaining": ["Ava", "Cora"],
        "initial_tally": [],
        "nullified_votes": 1,
        "revote_tally": [],
        "resolution": Resolution.ROCKS,
        "tied_contestants": [],
        "revote_voters": ["Ava", "Ben"],
        "rock_drawers": ["Ava", "Ben"],
        "fire_contestants": ["Ava", "Ben"],
        "needed_facts": [],
    }
    wrong = replace(made, outcome=replace(made.outcome, **{field: changes[field]}))
    assert not verifier.verify_task("scenario-outcome", given, wrong, None, "")["valid"]


@pytest.mark.parametrize(
    "mutation",
    [
        "tied_revoter",
        "revote_wrong_target",
        "rock_loser_tied",
        "rock_loser_immune",
        "consensus_non_tied",
        "both_deadlock_results",
        "unknown_rock_loser",
        "wrong_fire_winner",
        "duplicate_fire_pair",
        "fire_without_pair",
        "forced_fire_votes",
        "wrong_final_four_size",
        "final_four_items",
        "fire_pair_immune",
        "unique_vote_extra_result",
        "bad_name",
        "missing_vote",
        "self_vote",
        "illegal_extra_target",
        "reused_item",
    ],
)
def test_invalid_facts_are_rejected(mutation, tmp_path):
    name = "deadlock"
    if mutation in (
        "wrong_fire_winner",
        "duplicate_fire_pair",
        "fire_without_pair",
        "forced_fire_votes",
        "fire_pair_immune",
    ):
        name = "forced-fire-winner-unknown"
    elif mutation in ("wrong_final_four_size", "final_four_items"):
        name = "four-vote-fire-pending"
    elif mutation in (
        "unique_vote_extra_result",
        "bad_name",
        "missing_vote",
        "self_vote",
        "illegal_extra_target",
        "reused_item",
    ):
        name = "idol-on-other"
    raw = json.loads((CASES / f"{name}.input.json").read_text())
    facts = {"consensus_eliminated": None, "rock_draw_loser": None, "fire_participants": [], "fire_winner": None}
    if raw["resolution_facts"] is None:
        raw["resolution_facts"] = facts
    if mutation == "tied_revoter":
        raw["council"]["revotes"][0]["voter"] = "Ava"
    elif mutation == "revote_wrong_target":
        raw["council"]["revotes"][0]["target"] = "Drew"
    elif mutation == "rock_loser_tied":
        raw["resolution_facts"]["rock_draw_loser"] = "Ava"
    elif mutation == "rock_loser_immune":
        raw["council"]["challenge_immune"] = ["Cora"]
        raw["resolution_facts"]["rock_draw_loser"] = "Cora"
    elif mutation == "consensus_non_tied":
        raw["resolution_facts"]["consensus_eliminated"] = "Cora"
    elif mutation == "both_deadlock_results":
        raw["resolution_facts"].update(consensus_eliminated="Ben", rock_draw_loser="Cora")
    elif mutation == "unknown_rock_loser":
        raw["resolution_facts"]["rock_draw_loser"] = "Ghost"
    elif mutation == "wrong_fire_winner":
        raw["resolution_facts"]["fire_winner"] = "Ava"
    elif mutation == "duplicate_fire_pair":
        raw["resolution_facts"]["fire_participants"] = ["Ben", "Ben"]
    elif mutation == "fire_without_pair":
        raw["resolution_facts"].update(fire_participants=[], fire_winner="Ben")
    elif mutation == "forced_fire_votes":
        raw["council"]["votes"] = [{"voter": "Ava", "target": "Ben"}]
    elif mutation == "wrong_final_four_size":
        raw["council"]["contestants"].append("Eli")
    elif mutation == "final_four_items":
        raw["plays"] = [{"id": "idol", "owner": "Ava", "kind": "idol", "target": "Ava"}]
    elif mutation == "fire_pair_immune":
        raw["council"]["challenge_immune"] = ["Ben"]
    elif mutation == "unique_vote_extra_result":
        raw["resolution_facts"]["rock_draw_loser"] = "Cora"
    elif mutation == "bad_name":
        raw["council"]["contestants"][0] = " John"
    elif mutation == "missing_vote":
        raw["council"]["votes"].pop()
    elif mutation == "self_vote":
        raw["council"]["votes"][0]["target"] = "John"
    elif mutation == "illegal_extra_target":
        raw["plays"][0].update(kind="extra_vote", target="Esther")
    elif mutation == "reused_item":
        raw["plays"].append(copy.deepcopy(raw["plays"][0]))
    given = build_output(raw, TribalScenarioInput)
    assert not verifier.verify_input("resolve_tribal", given)["valid"]
    with pytest.raises(ValueError):
        resolve_tribal(given, tmp_path)


def test_ballot_and_roster_order_never_pick_the_loser(tmp_path):
    given = sample("you-go-home")
    original = resolve_tribal(given, tmp_path)
    for ballots in itertools.permutations(given.council.votes):
        result = resolve_tribal(replace(given, council=replace(given.council, votes=list(ballots))), tmp_path)
        assert result.outcome == original.outcome
    reversed_roster = replace(
        given, council=replace(given.council, contestants=list(reversed(given.council.contestants)))
    )
    result = resolve_tribal(reversed_roster, tmp_path)
    assert result.outcome.eliminated == original.outcome.eliminated == "John"
    assert {row.contestant: row.votes for row in result.outcome.initial_tally} == {
        row.contestant: row.votes for row in original.outcome.initial_tally
    }
    assert "priority_order" not in output_schema(TribalScenarioInput)["properties"]["council"]["properties"]


def test_deadlock_does_not_choose_a_random_loser(tmp_path):
    given = sample("deadlock")
    for names in (given.council.contestants, list(reversed(given.council.contestants))):
        result = resolve_tribal(replace(given, council=replace(given.council, contestants=names)), tmp_path)
        assert result.outcome.stage == CouncilStage.DEADLOCK
        assert result.outcome.eliminated is None and result.outcome.alliance_survives is None
        assert set(result.outcome.rock_drawers) == {"Cora", "Drew"}
        assert verifier.verify_task("scenario-outcome", result.scenario, result, None, "")["valid"]


def test_four_person_tribe_and_final_four_are_different_formats(tmp_path):
    ordinary = sample("deadlock")
    final_four = replace(ordinary, council=replace(ordinary.council, format=CouncilFormat.FINAL_FOUR_VOTE))
    a, b = resolve_tribal(ordinary, tmp_path), resolve_tribal(final_four, tmp_path)
    assert a.outcome.rock_drawers == ["Cora", "Drew"] and not a.outcome.fire_contestants
    assert b.outcome.fire_contestants == ["Ava", "Ben"] and not b.outcome.rock_drawers


def test_empty_resolution_object_does_not_change_a_unique_vote(tmp_path):
    given = sample()
    result = resolve_tribal(replace(given, resolution_facts=ResolutionFacts(None, None, [], None)), tmp_path)
    assert result.outcome == resolve_tribal(given, tmp_path).outcome


def test_four_person_ballots_agree_with_independent_verifier(tmp_path):
    given = sample("revote-required")
    names = given.council.contestants
    for targets in itertools.product(*[[other for other in names if other != name] for name in names]):
        votes = [Ballot(name, target) for name, target in zip(names, targets)]
        trial = replace(given, council=replace(given.council, votes=votes))
        result = resolve_tribal(trial, tmp_path)
        assert verifier.verify_task("scenario-outcome", trial, result, None, "")["valid"]
