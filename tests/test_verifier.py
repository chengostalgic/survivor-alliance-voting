"""Adversarial outputs, invalid councils, and contract-level malformed cases."""

import copy
import json
from dataclasses import replace
from pathlib import Path

import pytest
from slimconfig import build_output

import verifier
from contract import CouncilInput, CouncilOutput, Resolution, VoteCount
from plugin.vote import resolve_vote

SCENARIOS = Path(__file__).parent / "scenarios"


def example(name="majority"):
    return json.loads((SCENARIOS / f"{name}.input.json").read_text())


@pytest.mark.parametrize(
    "mutation",
    [
        {"contestants": ["Ava", "Ava"]},
        {"contestants": ["Ava"]},
        {"contestants": [""]},
        {"contestants": [" Ava", "Ben"]},
        {"contestants": ["Ava\n", "Ben"]},
        {"contestants": ["A" * 81, "Ben"]},
        {"alliance": []},
        {"alliance": ["Ghost"]},
        {"alliance": ["Ava", "Ava"]},
        {"challenge_immune": ["Ghost"]},
        {"idol_protected": ["Ghost"]},
        {"idol_protected": ["Ava", "Ava"]},
        {"challenge_immune": ["Drew"]},
        {"idol_protected": ["Ava", "Ben", "Cora", "Drew", "Eli"]},
        {"votes": []},
        {"revotes": [{"voter": "Ava", "target": "Ben"}]},
        {"rules": {"tie_rule": "priority", "priority_order": ["Ava"]}},
        {"rules": {"tie_rule": "priority", "priority_order": ["Ava", "Ben", "Cora", "Drew", "Drew"]}},
    ],
)
def test_semantically_invalid_inputs_are_rejected(mutation, tmp_path):
    raw = example()
    raw.update(mutation)
    given = build_output(raw, CouncilInput)
    assert verifier.verify_input("resolve_vote", given)["valid"] is False
    with pytest.raises(ValueError):
        resolve_vote(given, tmp_path)


@pytest.mark.parametrize("field,value", [("voter", "Ghost"), ("voter", "Ben"), ("target", "Ghost"), ("target", "Ava")])
def test_invalid_initial_ballots(field, value, tmp_path):
    raw = example()
    raw["votes"][0][field] = value
    given = build_output(raw, CouncilInput)
    assert not verifier.verify_input("resolve_vote", given)["valid"]
    with pytest.raises(ValueError):
        resolve_vote(given, tmp_path)


@pytest.mark.parametrize("change", ["missing", "duplicate", "tied_voter", "outside_target", "self_vote"])
def test_invalid_revotes(change, tmp_path):
    raw = example("revote")
    if change == "missing":
        raw["revotes"].pop()
    elif change == "duplicate":
        raw["revotes"][1]["voter"] = raw["revotes"][0]["voter"]
    elif change == "tied_voter":
        raw["revotes"][0]["voter"] = "Ava"
    elif change == "outside_target":
        raw["revotes"][0]["target"] = "Drew"
    else:
        raw["revotes"][0]["target"] = "Cora"
    given = build_output(raw, CouncilInput)
    assert not verifier.verify_input("resolve_vote", given)["valid"]
    with pytest.raises(ValueError):
        resolve_vote(given, tmp_path)


def test_empty_rock_pool_is_rejected(tmp_path):
    raw = example("zero-voter-revote")
    raw["rules"]["tie_rule"] = "revote_rocks"
    given = build_output(raw, CouncilInput)
    assert not verifier.verify_input("resolve_vote", given)["valid"]
    with pytest.raises(ValueError, match="rock"):
        resolve_vote(given, tmp_path)


@pytest.mark.parametrize(
    "field",
    [
        "eliminated",
        "alliance_survives",
        "alliance_remaining",
        "initial_tally",
        "nullified_votes",
        "revote_tally",
        "resolution",
        "deciding_candidates",
    ],
)
def test_each_output_field_is_checked(field, tmp_path):
    raw = example()
    expected = json.loads((SCENARIOS / "majority.expected.json").read_text())
    given = build_output(raw, CouncilInput)
    correct = build_output(expected, CouncilOutput)
    alternatives = {
        "eliminated": "Ben",
        "alliance_survives": False,
        "alliance_remaining": ["Ben", "Ava"],
        "initial_tally": [VoteCount("Ava", 999)],
        "nullified_votes": 1,
        "revote_tally": [VoteCount("Ava", 0)],
        "resolution": Resolution.ROCKS,
        "deciding_candidates": ["Ben"],
    }
    bad = replace(correct, **{field: alternatives[field]})
    for verdict in (
        verifier.verify_output("resolve_vote", given, bad, str(tmp_path)),
        verifier.verify_task("alliance-survival", given, bad, None, str(tmp_path)),
    ):
        assert verdict["valid"] is False
        assert verdict["score"] == 0


@pytest.mark.parametrize("name", ["idol", "rocks"])
def test_plausible_but_wrong_complete_results(name, tmp_path):
    given = build_output(example(name), CouncilInput)
    made = resolve_vote(given, tmp_path)
    wrong = replace(made, eliminated="Ben", alliance_survives=True, alliance_remaining=given.alliance)
    assert not verifier.verify_task("alliance-survival", given, wrong, None, "")["valid"]


@pytest.mark.parametrize("kind", ["missing", "null", "wrong_type", "unknown_rule", "extra"])
def test_malformed_input_is_rejected_by_contract(kind):
    raw = example()
    if kind == "missing":
        del raw["votes"]
    elif kind == "null":
        raw["alliance"] = None
    elif kind == "wrong_type":
        raw["votes"] = "Ava votes Drew"
    elif kind == "unknown_rule":
        raw["rules"]["tie_rule"] = "random"
    else:
        raw["unrecognized"] = True
    with pytest.raises((TypeError, ValueError)):
        build_output(raw, CouncilInput)


@pytest.mark.parametrize("kind", ["missing", "null", "wrong_type", "negative_string"])
def test_malformed_output_is_rejected_by_contract(kind):
    raw = json.loads((SCENARIOS / "majority.expected.json").read_text())
    if kind == "missing":
        del raw["eliminated"]
    elif kind == "null":
        raw = None
    elif kind == "wrong_type":
        raw["alliance_survives"] = "true"
    else:
        raw["initial_tally"][0]["votes"] = "-1"
    with pytest.raises((TypeError, ValueError)):
        build_output(raw, CouncilOutput)


def test_no_result_fails_verifier():
    given = build_output(example(), CouncilInput)
    assert not verifier.verify_task("alliance-survival", given, None, None, "")["valid"]


def test_repeatability_and_input_is_not_mutated(tmp_path):
    given = build_output(example("rocks"), CouncilInput)
    before = copy.deepcopy(given)
    made = resolve_vote(given, tmp_path)
    first = verifier.verify_task("alliance-survival", given, made, None, str(tmp_path))
    assert first == verifier.verify_task("alliance-survival", given, made, None, str(tmp_path))
    assert given == before


def test_unknown_entry_points_are_rejected():
    assert not verifier.verify_input("unknown", None)["valid"]
    assert not verifier.verify_output("unknown", None, None, "")["valid"]
    assert not verifier.verify_task("unknown", None, None, None, "")["valid"]
