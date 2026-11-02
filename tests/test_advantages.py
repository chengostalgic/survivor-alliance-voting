"""Hand-calculated advantage puzzles, interactions, and forged recommendations."""

import copy
import itertools
import json
from dataclasses import replace
from pathlib import Path

import pytest
from slimconfig import build_output, plain_output

import verifier
from contract import (
    AdvantageDecision,
    AdvantageInput,
    AdvantageOutput,
    AdvantagePlay,
)
from plugin.advantages import evaluate_plan, plan_advantages

CASES = Path(__file__).parent / "advantages"


def sample(name="idol-saves"):
    return json.loads((CASES / f"{name}.input.json").read_text())


@pytest.mark.parametrize("path", sorted(CASES.glob("*.input.json")), ids=lambda path: path.stem)
def test_hand_calculated_plans(path, tmp_path):
    given = build_output(json.loads(path.read_text()), AdvantageInput)
    before = copy.deepcopy(given)
    expected = json.loads(path.with_name(path.name.replace(".input.", ".expected.")).read_text())
    made = plan_advantages(given, tmp_path)
    assert plain_output(made) == expected
    assert verifier.verify_input("plan_advantages", given)["valid"]
    assert verifier.verify_output("plan_advantages", given, made, "")["valid"]
    assert verifier.verify_task("advantage-planner", given, made, None, "")["valid"]
    assert given == before and not list(tmp_path.iterdir())


@pytest.mark.parametrize(
    "field",
    [
        "scenario",
        "baseline",
        "decision",
        "minimum_items_needed",
        "plans_checked",
        "saving_plan_count",
        "minimal_saving_plan_count",
        "recommendations",
        "single_plays",
    ],
)
def test_every_planner_field_is_checked(field, tmp_path):
    given = build_output(sample(), AdvantageInput)
    made = plan_advantages(given, tmp_path)
    wrong = {
        "scenario": replace(given, inventory=[]),
        "baseline": replace(made.baseline, eliminated="Ben"),
        "decision": AdvantageDecision.HOLD,
        "minimum_items_needed": 0,
        "plans_checked": made.plans_checked - 1,
        "saving_plan_count": 0,
        "minimal_saving_plan_count": 0,
        "recommendations": [],
        "single_plays": [],
    }
    bad = replace(made, **{field: wrong[field]})
    for result in (
        verifier.verify_output("plan_advantages", given, bad, ""),
        verifier.verify_task("advantage-planner", given, bad, None, ""),
    ):
        assert not result["valid"] and result["score"] == 0


@pytest.mark.parametrize("change", ["unknown_item", "wrong_target", "reuse_item", "wrong_outcome", "false_minimum"])
def test_forged_plans_fail(change, tmp_path):
    given = build_output(sample(), AdvantageInput)
    made = plan_advantages(given, tmp_path)
    recommended = made.recommendations[0]
    if change == "unknown_item":
        recommended = replace(recommended, plays=[AdvantagePlay("made-up-idol", "Ava")])
    elif change == "wrong_target":
        recommended = replace(recommended, plays=[AdvantagePlay("Ava-idol", "Ben")])
    elif change == "reuse_item":
        recommended = replace(recommended, plays=recommended.plays * 2)
    elif change == "wrong_outcome":
        recommended = replace(recommended, outcome=made.baseline)
    else:
        bad = replace(
            made,
            decision=AdvantageDecision.NO_SAVING_PLAN,
            minimum_items_needed=None,
            saving_plan_count=0,
            minimal_saving_plan_count=0,
            recommendations=[],
        )
        assert not verifier.verify_task("advantage-planner", given, bad, None, "")["valid"]
        return
    assert not verifier.verify_task("advantage-planner", given, replace(made, recommendations=[recommended]), None, "")[
        "valid"
    ]


def test_holding_items_still_compares_wasteful_and_harmful_plays(tmp_path):
    given = build_output(sample("hold-and-backfire"), AdvantageInput)
    made = plan_advantages(given, tmp_path)
    assert made.decision == AdvantageDecision.HOLD and made.minimum_items_needed == 0
    assert made.recommendations[0].plays == [] and made.plans_checked == 3
    assert [row.alliance_survives for row in made.single_plays] == [True, False]


def test_extra_ballot_survives_its_owners_original_vote_being_blocked():
    given = build_output(sample("blocked-extra-owner"), AdvantageInput)
    result = evaluate_plan(given, [AdvantagePlay("Ava-block", "Ben"), AdvantagePlay("Ben-extra", "Ava")]).outcome
    assert result.eliminated == "Ava"
    assert [(row.contestant, row.votes) for row in result.initial_tally] == [
        ("Ava", 3),
        ("Ben", 0),
        ("Cora", 0),
        ("Drew", 2),
        ("Eli", 0),
    ]


def test_blocked_ballots_are_not_counted_as_idol_nullifications():
    given = build_output(sample("extra-vote-nullified"), AdvantageInput)
    result = evaluate_plan(given, [AdvantagePlay("Ava-block", "Cora"), AdvantagePlay("Ben-extra", "Ava")]).outcome
    assert result.eliminated == "Drew" and result.nullified_votes == 3
    assert sum(row.votes for row in result.initial_tally) == 2


def test_two_blocks_on_the_same_voter_remove_only_one_ballot():
    given = build_output(sample("many-minimum-plans"), AdvantageInput)
    result = evaluate_plan(given, [AdvantagePlay("Ava-block-1", "Cora"), AdvantagePlay("Ava-block-2", "Cora")]).outcome
    assert sum(row.votes for row in result.initial_tally) == 5
    assert result.eliminated == "Drew"


def test_two_idols_on_the_same_person_do_not_protect_both_allies():
    given = build_output(sample("two-idols-split-vote"), AdvantageInput)
    result = evaluate_plan(given, [AdvantagePlay("Ava-idol", "Ava"), AdvantagePlay("Ben-idol", "Ava")]).outcome
    assert result.eliminated == "Ben" and not result.alliance_survives


def test_search_limit_does_not_claim_three_item_plans_are_impossible(tmp_path):
    given = build_output(sample("two-item-search-limit"), AdvantageInput)
    made = plan_advantages(given, tmp_path)
    assert made.decision == AdvantageDecision.NO_SAVING_PLAN and made.minimum_items_needed is None
    # This is a legal three-item outcome, deliberately outside the planner's search budget.
    triple = evaluate_plan(given, [AdvantagePlay(item.id, "Drew") for item in given.inventory]).outcome
    assert triple.alliance_survives and triple.eliminated == "Drew"


def test_complete_counts_and_canonical_capped_recommendations(tmp_path):
    given = build_output(sample("many-minimum-plans"), AdvantageInput)
    made = plan_advantages(given, tmp_path)
    assert made.plans_checked == 91 and made.saving_plan_count == 36
    assert made.minimal_saving_plan_count == 9 and len(made.recommendations) == 5
    for bad in (
        replace(made, minimal_saving_plan_count=5),
        replace(made, recommendations=made.recommendations[:4]),
        replace(made, recommendations=list(reversed(made.recommendations))),
        replace(made, single_plays=list(reversed(made.single_plays))),
        replace(made, single_plays=[replace(made.single_plays[0], owner="Drew"), *made.single_plays[1:]]),
    ):
        assert not verifier.verify_task("advantage-planner", given, bad, None, "")["valid"]


@pytest.mark.parametrize(
    "change",
    [
        "too_many",
        "duplicate_id",
        "empty_id",
        "long_id",
        "untrimmed_id",
        "unknown_owner",
        "empty_targets",
        "duplicate_target",
        "unknown_target",
        "self_extra",
        "self_block",
        "immune_extra",
        "revote",
    ],
)
def test_invalid_inventory_and_rules_are_rejected(change, tmp_path):
    raw = sample()
    original = raw["inventory"][0]
    if change == "too_many":
        raw["inventory"] = [{**original, "id": f"idol-{i}"} for i in range(4)]
    elif change == "duplicate_id":
        raw["inventory"].append(dict(original))
    elif change == "empty_id":
        original["id"] = ""
    elif change == "long_id":
        original["id"] = "x" * 41
    elif change == "untrimmed_id":
        original["id"] = " idol"
    elif change == "unknown_owner":
        original["owner"] = "Drew"
    elif change == "empty_targets":
        original["allowed_targets"] = []
    elif change == "duplicate_target":
        original["allowed_targets"] = ["Ava", "Ava"]
    elif change == "unknown_target":
        original["allowed_targets"] = ["Ghost"]
    elif change in ("self_extra", "self_block"):
        original["kind"] = "extra_vote" if change == "self_extra" else "vote_block"
        original["allowed_targets"] = ["Ava"]
    elif change == "immune_extra":
        raw["council"]["challenge_immune"] = ["Cora"]
        original.update(kind="extra_vote", allowed_targets=["Cora"])
    else:
        raw["council"]["rules"]["tie_rule"] = "revote_priority"
    given = build_output(raw, AdvantageInput)
    assert not verifier.verify_input("plan_advantages", given)["valid"]
    with pytest.raises(ValueError):
        plan_advantages(given, tmp_path)


def test_missing_and_malformed_values_are_rejected():
    given = build_output(sample(), AdvantageInput)
    assert not verifier.verify_task("advantage-planner", given, None, None, "")["valid"]
    with pytest.raises((TypeError, ValueError)):
        build_output({"council": sample()["council"]}, AdvantageInput)
    with pytest.raises((TypeError, ValueError)):
        build_output({"decision": "play"}, AdvantageOutput)
    bad = sample()
    bad["inventory"][0]["kind"] = "super-idol"
    with pytest.raises((TypeError, ValueError)):
        build_output(bad, AdvantageInput)


def test_target_list_order_does_not_change_comparison_or_recommendation_order(tmp_path):
    raw = sample("compare-all-types")
    before = plan_advantages(build_output(raw, AdvantageInput), tmp_path)
    for item in raw["inventory"]:
        item["allowed_targets"].reverse()
    after = plan_advantages(build_output(raw, AdvantageInput), tmp_path)
    assert after.recommendations == before.recommendations and after.single_plays == before.single_plays


def test_largest_supported_search(tmp_path):
    names = [f"P{i:02}" for i in range(24)]
    raw = sample()
    raw["council"] = {
        "contestants": names,
        "alliance": names,
        "votes": [{"voter": name, "target": names[1] if i == 0 else names[0]} for i, name in enumerate(names)],
        "challenge_immune": [],
        "idol_protected": [],
        "revotes": [],
        "rules": {"tie_rule": "priority", "priority_order": names},
    }
    raw["inventory"] = [
        {"id": f"idol-{i}", "owner": names[0], "kind": "idol", "allowed_targets": names} for i in range(3)
    ]
    given = build_output(raw, AdvantageInput)
    made = plan_advantages(given, tmp_path)
    assert made.plans_checked == 1801 and len(made.single_plays) == 72
    assert made.saving_plan_count == 0 and made.decision == AdvantageDecision.NO_SAVING_PLAN
    assert verifier.verify_task("advantage-planner", given, made, None, "")["valid"]


def test_all_four_person_ballots_with_mixed_advantages(tmp_path):
    names = ["A", "B", "C", "D"]
    for targets in itertools.product(*[[name for name in names if name != voter] for voter in names]):
        given = build_output(
            {
                "council": {
                    "contestants": names,
                    "alliance": ["A", "B"],
                    "votes": [{"voter": voter, "target": target} for voter, target in zip(names, targets)],
                    "challenge_immune": [],
                    "idol_protected": [],
                    "revotes": [],
                    "rules": {"tie_rule": "priority", "priority_order": names},
                },
                "inventory": [
                    {"id": "idol", "owner": "A", "kind": "idol", "allowed_targets": ["A", "B"]},
                    {"id": "extra", "owner": "B", "kind": "extra_vote", "allowed_targets": ["C", "D"]},
                    {"id": "block", "owner": "A", "kind": "vote_block", "allowed_targets": ["B", "C", "D"]},
                ],
            },
            AdvantageInput,
        )
        made = plan_advantages(given, tmp_path)
        assert made.plans_checked == 24
        assert verifier.verify_task("advantage-planner", given, made, None, "")["valid"]
        assert all(len(plan.plays) <= 2 for plan in made.recommendations)
