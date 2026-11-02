"""Fixed hypothetical votes and actual assumed plays, including correct losing outcomes."""

import copy
import itertools
import json
from dataclasses import replace
from pathlib import Path

import pytest
from slimconfig import build_output, plain_output

import verifier
from contract import (
    AdvantageKind,
    Ballot,
    PersonalOutcome,
    PlayedAdvantage,
    ScenarioInput,
    ScenarioOutput,
)
from plugin.scenario import evaluate_scenario

CASES = Path(__file__).parent / "fixed_scenarios"


def sample(name="idol-on-someone-else"):
    return json.loads((CASES / f"{name}.input.json").read_text())


@pytest.mark.parametrize("path", sorted(CASES.glob("*.input.json")), ids=lambda path: path.stem)
def test_hand_calculated_scenarios(path, tmp_path):
    given = build_output(json.loads(path.read_text()), ScenarioInput)
    before = copy.deepcopy(given)
    expected = json.loads(path.with_name(path.name.replace(".input.", ".expected.")).read_text())
    made = evaluate_scenario(given, tmp_path)
    assert plain_output(made) == expected
    assert verifier.verify_input("evaluate_scenario", given)["valid"]
    assert verifier.verify_output("evaluate_scenario", given, made, "")["valid"]
    assert verifier.verify_task("scenario-outcome", given, made, None, "")["valid"]
    assert given == before and not list(tmp_path.iterdir())


@pytest.mark.parametrize(
    "field", ["scenario", "outcome", "personal_outcome", "idol_recipients", "blocked_voters", "extra_votes"]
)
def test_every_returned_field_is_verified(field, tmp_path):
    given = build_output(sample(), ScenarioInput)
    made = evaluate_scenario(given, tmp_path)
    changes = {
        "scenario": replace(given, plays=[]),
        "outcome": replace(made.outcome, eliminated="John"),
        "personal_outcome": PersonalOutcome.YOU_GO_HOME,
        "idol_recipients": ["Esther"],
        "blocked_voters": ["Cora"],
        "extra_votes": [Ballot("Esther", "John")],
    }
    forged = replace(made, **{field: changes[field]})
    assert not verifier.verify_output("evaluate_scenario", given, forged, "")["valid"]
    assert not verifier.verify_task("scenario-outcome", given, forged, None, "")["valid"]


@pytest.mark.parametrize(
    "mutation",
    [
        "reused_item",
        "unknown_owner",
        "unknown_target",
        "self_extra",
        "self_block",
        "immune_extra",
        "unlisted_protection",
        "unknown_perspective",
        "opponent_perspective",
        "missing_vote",
        "missing_priority",
        "too_many_items",
        "empty_item_id",
        "padded_item_id",
        "long_item_id",
        "nonprintable_item_id",
        "all_protected",
    ],
)
def test_invalid_assumptions_are_rejected(mutation, tmp_path):
    raw = sample()
    play = raw["plays"][0]
    if mutation == "reused_item":
        raw["plays"].append(copy.deepcopy(play))
    elif mutation == "unknown_owner":
        play["owner"] = "Ghost"
    elif mutation == "unknown_target":
        play["target"] = "Ghost"
    elif mutation in ("self_extra", "self_block"):
        play.update(kind="extra_vote" if mutation == "self_extra" else "vote_block", target=play["owner"])
    elif mutation == "immune_extra":
        raw["council"]["challenge_immune"] = ["Cora"]
        play.update(kind="extra_vote", target="Cora")
    elif mutation == "unlisted_protection":
        raw["council"]["idol_protected"] = ["John"]
    elif mutation in ("unknown_perspective", "opponent_perspective"):
        raw["perspective"] = "Ghost" if mutation == "unknown_perspective" else "Cora"
    elif mutation == "missing_vote":
        raw["council"]["votes"].pop()
    elif mutation == "missing_priority":
        raw["council"]["rules"]["priority_order"].pop()
    elif mutation == "too_many_items":
        raw["plays"] = [dict(play, id=f"item-{i}") for i in range(25)]
    elif mutation == "all_protected":
        raw["plays"] = [dict(play, id=f"item-{i}", target=name) for i, name in enumerate(raw["council"]["contestants"])]
    else:
        play["id"] = {
            "empty_item_id": "",
            "padded_item_id": " padded",
            "long_item_id": "x" * 41,
            "nonprintable_item_id": "idol\n",
        }[mutation]
    given = build_output(raw, ScenarioInput)
    assert not verifier.verify_input("evaluate_scenario", given)["valid"]
    with pytest.raises(ValueError):
        evaluate_scenario(given, tmp_path)


@pytest.mark.parametrize("mutation", ["missing_plays", "missing_target", "invalid_kind", "wrong_outcome_type"])
def test_malformed_contracts_are_rejected(mutation):
    raw = sample()
    target_type = ScenarioInput
    if mutation == "missing_plays":
        raw.pop("plays")
    elif mutation == "missing_target":
        raw["plays"][0].pop("target")
    elif mutation == "invalid_kind":
        raw["plays"][0]["kind"] = "steal_vote"
    else:
        raw = json.loads((CASES / "you-go-home.expected.json").read_text())
        raw["outcome"]["alliance_survives"] = "yes"
        target_type = ScenarioOutput
    with pytest.raises((ValueError, TypeError)):
        build_output(raw, target_type)


def test_unplayed_idol_has_no_effect_and_recipient_is_not_owner(tmp_path):
    raw = sample()
    held = build_output(dict(raw, plays=[]), ScenarioInput)
    played = build_output(raw, ScenarioInput)
    assert evaluate_scenario(held, tmp_path).outcome.eliminated == "John"
    result = evaluate_scenario(played, tmp_path)
    assert result.idol_recipients == ["John"]
    assert result.outcome.eliminated == "Drew"
    assert result.outcome.nullified_votes == 3


def test_play_order_does_not_change_effects(tmp_path):
    given = build_output(sample("idol-nullifies-extra"), ScenarioInput)
    first = evaluate_scenario(given, tmp_path)
    second = evaluate_scenario(replace(given, plays=list(reversed(given.plays))), tmp_path)
    assert first.outcome == second.outcome
    assert first.idol_recipients == second.idol_recipients


def test_maximum_item_count_is_supported(tmp_path):
    given = build_output(sample("you-go-home"), ScenarioInput)
    given = replace(
        given, plays=[PlayedAdvantage(f"extra-{i}", "John", AdvantageKind.EXTRA_VOTE, "Drew") for i in range(24)]
    )
    result = evaluate_scenario(given, tmp_path)
    assert [row.votes for row in result.outcome.initial_tally] == [3, 0, 0, 26, 0]
    assert len(result.extra_votes) == 24
    assert verifier.verify_task("scenario-outcome", given, result, None, "")["valid"]


def test_all_four_person_ballots_with_explicit_mixed_plays(tmp_path):
    raw = json.loads((Path(__file__).parent / "scenarios/revote.input.json").read_text())
    raw["rules"]["tie_rule"] = "priority"
    raw["revotes"] = []
    names = raw["contestants"]
    # 81 ordinary vote patterns. Play roles cross alliance boundaries; an extra
    # ballot survives its owner's original ballot being blocked.
    for targets in itertools.product(*[[other for other in names if other != name] for name in names]):
        raw["votes"] = [{"voter": name, "target": target} for name, target in zip(names, targets)]
        given = build_output(
            {
                "council": raw,
                "perspective": "Ava",
                "plays": [
                    {"id": "idol", "owner": "Ben", "kind": "idol", "target": "Ava"},
                    {"id": "block", "owner": "Cora", "kind": "vote_block", "target": "Drew"},
                    {"id": "extra", "owner": "Drew", "kind": "extra_vote", "target": "Ben"},
                ],
            },
            ScenarioInput,
        )
        result = evaluate_scenario(given, tmp_path)
        assert verifier.verify_task("scenario-outcome", given, result, None, "")["valid"]
