"""Exercise user-visible rescue messages against the documented kit interface."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

KIT_STUB = """
export const h = (tag, attrs = {}, ...children) => ({tag, attrs, children});
export const statusPill = (text) => h("span", {text});
export const disclosure = (options, ...children) => h("details", {}, options.summary, children);
export const dataTable = ({columns, rows}) => ({
  element: h("table", {}, rows.map(row => columns.map(column => row[column.key])))
});
"""

DRAW = """
import {readFileSync} from "node:fs";
import renderers from "./renderers.mjs";
const value = JSON.parse(readFileSync("sample.json", "utf8"));
const verdict = JSON.parse(readFileSync("verdict.json", "utf8"));
function text(node) {
  if (node == null || node === false) return "";
  if (Array.isArray(node)) return node.map(text).join(" ");
  if (typeof node !== "object") return String(node);
  return (node.attrs?.text ?? "") + " " + text(node.children);
}
console.log(text(renderers[process.argv[2] || "RescueOutput"](value, {verdict})));
"""


@pytest.mark.skipif(shutil.which("node") is None, reason="renderer smoke test needs Node")
@pytest.mark.parametrize(
    "name,valid,words",
    [
        ("save-one", True, "A single vote can save your alliance"),
        ("already-safe", True, "No change is needed"),
        ("impossible", True, "No legal vote change"),
        ("save-one", False, "Verification failed"),
    ],
)
def test_rescue_renderer_messages(tmp_path, name, valid, words):
    sample = json.loads((ROOT / "tests/rescues" / f"{name}.expected.json").read_text())
    source = (ROOT / "ui/renderers.js").read_text().replace("./kit/components.js", "./components.mjs")
    (tmp_path / "renderers.mjs").write_text(source)
    (tmp_path / "components.mjs").write_text(KIT_STUB)
    (tmp_path / "draw.mjs").write_text(DRAW)
    (tmp_path / "sample.json").write_text(json.dumps(sample))
    (tmp_path / "verdict.json").write_text(
        json.dumps({"valid": valid, "message": "check failed" if not valid else "valid"})
    )
    result = subprocess.run(["node", "draw.mjs"], cwd=tmp_path, capture_output=True, text=True, check=True)
    assert words in result.stdout
    if valid:
        assert "Check the interpreted scenario" in result.stdout and "Tie priority" in result.stdout
    else:
        assert "A single vote can save" not in result.stdout


@pytest.mark.skipif(shutil.which("node") is None, reason="renderer smoke test needs Node")
@pytest.mark.parametrize(
    "name,valid,words",
    [
        ("hold-and-backfire", True, "Keep your remaining items"),
        ("idol-saves", True, "One item can save everyone"),
        ("two-idols-split-vote", True, "Two items are needed"),
        ("no-inventory", True, "No saving plan using up to two items"),
        ("idol-saves", False, "Verification failed"),
    ],
)
def test_advantage_renderer_messages(tmp_path, name, valid, words):
    sample = json.loads((ROOT / "tests/advantages" / f"{name}.expected.json").read_text())
    source = (ROOT / "ui/renderers.js").read_text().replace("./kit/components.js", "./components.mjs")
    (tmp_path / "renderers.mjs").write_text(source)
    (tmp_path / "components.mjs").write_text(KIT_STUB)
    (tmp_path / "draw.mjs").write_text(DRAW)
    (tmp_path / "sample.json").write_text(json.dumps(sample))
    (tmp_path / "verdict.json").write_text(
        json.dumps({"valid": valid, "message": "check failed" if not valid else "valid"})
    )
    result = subprocess.run(
        ["node", "draw.mjs", "AdvantageOutput"], cwd=tmp_path, capture_output=True, text=True, check=True
    )
    assert words in result.stdout
    if valid:
        assert "How these advantages work" in result.stdout
        assert "Idol:" in result.stdout and "Extra vote:" in result.stdout and "Vote block:" in result.stdout
        assert "Check the interpreted council and inventory" in result.stdout
    else:
        assert "An advantage play saves" not in result.stdout


@pytest.mark.skipif(shutil.which("node") is None, reason="renderer smoke test needs Node")
@pytest.mark.parametrize(
    "name,valid,words",
    [
        ("you-go-home", True, "You go home in this scenario"),
        ("ally-goes-home", True, "An ally goes home in this scenario"),
        ("idol-on-someone-else", True, "You and your whole alliance stay"),
        ("identity-unspecified", True, "An alliance member goes home"),
        ("idol-on-someone-else", False, "Verification failed"),
    ],
)
def test_scenario_renderer_messages(tmp_path, name, valid, words):
    sample = json.loads((ROOT / "tests/fixed_scenarios" / f"{name}.expected.json").read_text())
    source = (ROOT / "ui/renderers.js").read_text().replace("./kit/components.js", "./components.mjs")
    (tmp_path / "renderers.mjs").write_text(source)
    (tmp_path / "components.mjs").write_text(KIT_STUB)
    (tmp_path / "draw.mjs").write_text(DRAW)
    (tmp_path / "sample.json").write_text(json.dumps(sample))
    (tmp_path / "verdict.json").write_text(
        json.dumps({"valid": valid, "message": "valid" if valid else "check failed"})
    )
    result = subprocess.run(
        ["node", "draw.mjs", "ScenarioOutput"], cwd=tmp_path, capture_output=True, text=True, check=True
    )
    assert words in result.stdout
    if valid:
        assert "Under your assumed votes and plays" in result.stdout
        assert "Check the assumed scenario" in result.stdout
        assert "does not establish that people will actually vote" in result.stdout
    else:
        assert "You and your whole alliance stay" not in result.stdout
