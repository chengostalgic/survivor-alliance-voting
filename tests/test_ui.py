"""Exercise user-visible tribal messages against the documented kit interface."""

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
console.log(text(renderers[process.argv[2] || "TribalScenarioOutput"](value, {verdict})));
"""


@pytest.mark.skipif(shutil.which("node") is None, reason="renderer smoke test needs Node")
@pytest.mark.parametrize(
    "name,words",
    [
        ("idol-on-other", "Drew goes home in this scenario"),
        ("revote-required", "Revote required"),
        ("deadlock", "No random loser has been chosen"),
        ("four-vote-fire-pending", "Fire-making result pending"),
        ("forced-fire-resolved", "Cora goes home in this scenario"),
    ],
)
def test_standard_tribal_renderer(tmp_path, name, words):
    sample = json.loads((ROOT / "tests/tribal" / f"{name}.expected.json").read_text())
    source = (ROOT / "ui/renderers.js").read_text().replace("./kit/components.js", "./components.mjs")
    (tmp_path / "renderers.mjs").write_text(source)
    (tmp_path / "components.mjs").write_text(KIT_STUB)
    (tmp_path / "draw.mjs").write_text(DRAW)
    (tmp_path / "sample.json").write_text(json.dumps(sample))
    (tmp_path / "verdict.json").write_text(json.dumps({"valid": True}))
    result = subprocess.run(
        ["node", "draw.mjs", "TribalScenarioOutput"], cwd=tmp_path, capture_output=True, text=True, check=True
    )
    assert words in result.stdout
    assert "priority" not in result.stdout.lower()
