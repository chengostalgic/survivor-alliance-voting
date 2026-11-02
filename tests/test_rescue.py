"""Hand-calculated strategic cases and adversarial rescue claims."""

import copy
import itertools
import json
from dataclasses import replace
from pathlib import Path

import pytest
from slimconfig import build_output, plain_output

import verifier
from contract import CouncilInput, RescueOutput, RescueStatus, TieRule
from plugin.rescue import find_rescue

CASES = Path(__file__).parent / "rescues"


def sample(name="save-one"):
    return json.loads((CASES / f"{name}.input.json").read_text())


@pytest.mark.parametrize("path", sorted(CASES.glob("*.input.json")), ids=lambda path: path.stem)
def test_hand_calculated_rescues(path, tmp_path):
    raw = json.loads(path.read_text())
    expected = json.loads(path.with_name(path.name.replace(".input.", ".expected.")).read_text())
    given = build_output(raw, CouncilInput)
    before = copy.deepcopy(given)
    made = find_rescue(given, tmp_path)
    assert plain_output(made) == expected
    assert verifier.verify_input("find_rescue", given)["valid"]
    assert verifier.verify_output("find_rescue", given, made, str(tmp_path))["valid"]
    assert verifier.verify_task("single-vote-rescue", given, made, None, str(tmp_path))["valid"]
    assert given == before
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize(
    "field", ["council", "baseline", "status", "tested_changes", "saving_change_count", "suggestions"]
)
def test_every_rescue_output_field_is_checked(field, tmp_path):
    given = build_output(sample(), CouncilInput)
    made = find_rescue(given, tmp_path)
    bad_fields = {
        "council": replace(given, alliance=["Ava"]),
        "baseline": replace(made.baseline, eliminated="Ben"),
        "status": RescueStatus.IMPOSSIBLE,
        "tested_changes": 5,
        "saving_change_count": 0,
        "suggestions": [],
    }
    bad = replace(made, **{field: bad_fields[field]})
    for verdict in (
        verifier.verify_output("find_rescue", given, bad, ""),
        verifier.verify_task("single-vote-rescue", given, bad, None, ""),
    ):
        assert not verdict["valid"] and verdict["score"] == 0


@pytest.mark.parametrize("field,value", [("voter", "Cora"), ("from_target", "Drew"), ("to_target", "Ben")])
def test_forged_move_is_rejected(field, value, tmp_path):
    given = build_output(sample(), CouncilInput)
    made = find_rescue(given, tmp_path)
    bad = replace(made, suggestions=[replace(made.suggestions[0], **{field: value})])
    assert not verifier.verify_task("single-vote-rescue", given, bad, None, "")["valid"]


def test_forged_move_outcome_and_false_impossibility_are_rejected(tmp_path):
    given = build_output(sample(), CouncilInput)
    made = find_rescue(given, tmp_path)
    wrong_move = replace(made.suggestions[0], outcome=made.baseline)
    assert not verifier.verify_task("single-vote-rescue", given, replace(made, suggestions=[wrong_move]), None, "")[
        "valid"
    ]
    assert not verifier.verify_task(
        "single-vote-rescue",
        given,
        replace(made, status=RescueStatus.IMPOSSIBLE, saving_change_count=0, suggestions=[]),
        None,
        "",
    )["valid"]


def test_suggestions_are_capped_complete_and_canonically_ordered(tmp_path):
    given = build_output(sample("many-saving-moves"), CouncilInput)
    made = find_rescue(given, tmp_path)
    assert made.saving_change_count == 8 and len(made.suggestions) == 5
    for bad in (
        replace(made, saving_change_count=5),
        replace(made, suggestions=list(reversed(made.suggestions))),
        replace(made, suggestions=made.suggestions[:4]),
    ):
        assert not verifier.verify_task("single-vote-rescue", given, bad, None, "")["valid"]


@pytest.mark.parametrize("tie_rule", [TieRule.REVOTE_PRIORITY, TieRule.REVOTE_ROCKS])
def test_counterfactuals_require_explicit_priority_rules(tie_rule, tmp_path):
    given = build_output(sample(), CouncilInput)
    given = replace(given, rules=replace(given.rules, tie_rule=tie_rule))
    assert not verifier.verify_input("find_rescue", given)["valid"]
    with pytest.raises(ValueError, match="priority"):
        find_rescue(given, tmp_path)


def test_missing_ballot_and_missing_output_are_rejected(tmp_path):
    given = build_output(sample(), CouncilInput)
    assert not verifier.verify_input("find_rescue", replace(given, votes=given.votes[:-1]))["valid"]
    with pytest.raises(ValueError):
        find_rescue(replace(given, votes=given.votes[:-1]), tmp_path)
    assert not verifier.verify_task("single-vote-rescue", given, None, None, "")["valid"]
    with pytest.raises((TypeError, ValueError)):
        build_output({"status": "rescuable"}, RescueOutput)


def test_no_legal_changes_at_two_person_boundary(tmp_path):
    raw = sample()
    raw.update(
        {
            "contestants": ["Ava", "Ben"],
            "alliance": ["Ava"],
            "votes": [{"voter": "Ava", "target": "Ben"}, {"voter": "Ben", "target": "Ava"}],
            "rules": {"tie_rule": "priority", "priority_order": ["Ava", "Ben"]},
        }
    )
    given = build_output(raw, CouncilInput)
    made = find_rescue(given, tmp_path)
    assert made.status == RescueStatus.IMPOSSIBLE and made.tested_changes == 0
    assert verifier.verify_task("single-vote-rescue", given, made, None, "")["valid"]


def test_maximum_roster_search_and_suggestion_limit(tmp_path):
    names = [f"P{i:02}" for i in range(24)]
    given = build_output(
        {
            "contestants": names,
            "alliance": names[:-1],
            "votes": [
                {"voter": voter, "target": names[0] if 1 <= i <= 11 or i == 23 else names[-1]}
                for i, voter in enumerate(names)
            ],
            "challenge_immune": [],
            "idol_protected": [],
            "revotes": [],
            "rules": {"tie_rule": "priority", "priority_order": names},
        },
        CouncilInput,
    )
    made = find_rescue(given, tmp_path)
    assert made.baseline.eliminated == "P00"
    assert made.status == RescueStatus.RESCUABLE
    assert made.tested_changes == 506 and made.saving_change_count == 242
    assert len(made.suggestions) == 5
    assert verifier.verify_task("single-vote-rescue", given, made, None, "")["valid"]


def test_vote_and_alliance_order_do_not_change_the_search(tmp_path):
    raw = sample("many-saving-moves")
    before = find_rescue(build_output(raw, CouncilInput), tmp_path)
    raw["votes"].reverse()
    raw["alliance"].reverse()
    after = find_rescue(build_output(raw, CouncilInput), tmp_path)
    assert after.suggestions == before.suggestions
    assert after.saving_change_count == before.saving_change_count
    assert after.tested_changes == before.tested_changes


def test_all_four_person_ballots_and_alliances(tmp_path):
    names = ["A", "B", "C", "D"]
    for targets in itertools.product(*[[name for name in names if name != voter] for voter in names]):
        for size in range(1, 5):
            for alliance in itertools.combinations(names, size):
                given = build_output(
                    {
                        "contestants": names,
                        "alliance": list(alliance),
                        "votes": [{"voter": voter, "target": target} for voter, target in zip(names, targets)],
                        "challenge_immune": [],
                        "idol_protected": [],
                        "revotes": [],
                        "rules": {"tie_rule": "priority", "priority_order": names},
                    },
                    CouncilInput,
                )
                made = find_rescue(given, tmp_path)
                assert verifier.verify_task("single-vote-rescue", given, made, None, "")["valid"]
                if made.baseline.alliance_survives:
                    assert made.status == RescueStatus.ALREADY_SAFE and made.tested_changes == 0
                else:
                    assert made.tested_changes == 2 * len(alliance)
                for move in made.suggestions:
                    assert move.voter in alliance and move.to_target != move.voter
                    assert move.from_target != move.to_target and move.outcome.alliance_survives
