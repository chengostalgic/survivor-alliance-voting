"""Hand-computed outcomes and exhaustive small-council cross-checks."""

import itertools
import json
from pathlib import Path

import pytest
from slimconfig import build_output, plain_output

import verifier
from contract import CouncilInput, CouncilOutput
from plugin.vote import resolve_vote

SCENARIOS = Path(__file__).parent / "scenarios"


@pytest.mark.parametrize("path", sorted(SCENARIOS.glob("*.input.json")), ids=lambda p: p.stem)
def test_hand_computed_councils(path, tmp_path):
    raw = json.loads(path.read_text())
    expected = json.loads(path.with_name(path.name.replace(".input.", ".expected.")).read_text())
    given = build_output(raw, CouncilInput)
    made = resolve_vote(given, tmp_path)
    assert plain_output(made) == expected
    assert verifier.verify_input("resolve_vote", given)["valid"]
    assert verifier.verify_output("resolve_vote", given, made, str(tmp_path))["valid"]
    assert verifier.verify_task("alliance-survival", given, build_output(expected, CouncilOutput), None, "")["valid"]
    assert list(tmp_path.iterdir()) == []


def test_all_four_person_ballots_and_legal_revotes(tmp_path):
    """Enumerate every legal initial ballot and every possible required revote."""
    names = ["A", "B", "C", "D"]
    checked = 0
    for targets in itertools.product(*[[name for name in names if name != voter] for voter in names]):
        highest = max(targets.count(name) for name in names)
        tied = [name for name in names if targets.count(name) == highest]
        voters = [name for name in names if name not in tied]
        for rule in ("priority", "revote_priority", "revote_rocks"):
            options = itertools.product(tied, repeat=len(voters)) if len(tied) > 1 and rule != "priority" else [()]
            for choices in options:
                given = build_output(
                    {
                        "contestants": names,
                        "alliance": ["A", "C"],
                        "votes": [{"voter": voter, "target": target} for voter, target in zip(names, targets)],
                        "challenge_immune": [],
                        "idol_protected": [],
                        "rules": {"tie_rule": rule, "priority_order": ["D", "C", "B", "A"]},
                        "revotes": [{"voter": voter, "target": target} for voter, target in zip(voters, choices)],
                    },
                    CouncilInput,
                )
                valid = verifier.verify_input("resolve_vote", given)["valid"]
                if not valid:
                    with pytest.raises(ValueError, match="rock"):
                        resolve_vote(given, tmp_path)
                    continue
                made = resolve_vote(given, tmp_path)
                assert verifier.verify_task("alliance-survival", given, made, None, "")["valid"]
                assert sum(row.votes for row in made.initial_tally) == 4
                assert made.alliance_survives == (made.eliminated not in given.alliance)
                if made.resolution.value == "rocks":
                    assert made.eliminated not in tied
                checked += 1
    assert checked > 300


@pytest.mark.parametrize("size", [2, 24])
def test_roster_size_boundaries(size, tmp_path):
    names = [f"P{i:02}" for i in range(size)]
    given = build_output(
        {
            "contestants": names,
            "alliance": names,
            "votes": [{"voter": name, "target": names[1] if i == 0 else names[0]} for i, name in enumerate(names)],
            "challenge_immune": [],
            "idol_protected": [],
            "rules": {"tie_rule": "priority", "priority_order": names},
            "revotes": [],
        },
        CouncilInput,
    )
    result = resolve_vote(given, tmp_path)
    assert result.eliminated == names[0]
    assert result.alliance_survives is False
    assert result.alliance_remaining == names[1:]
    assert verifier.verify_task("alliance-survival", given, result, None, "")["valid"]


def test_ballot_and_alliance_order_do_not_change_outcome(tmp_path):
    raw = json.loads((SCENARIOS / "majority.input.json").read_text())
    result = resolve_vote(build_output(raw, CouncilInput), tmp_path)
    raw["votes"].reverse()
    raw["alliance"].reverse()
    assert resolve_vote(build_output(raw, CouncilInput), tmp_path) == result
