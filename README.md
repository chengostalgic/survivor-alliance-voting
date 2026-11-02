# Survivor Alliance

Does **every member of your alliance** survive one Survivor-style tribal council?

Supply the contestants, alliance, initial ballots, immunity, and explicit tie rules.
The result identifies who leaves, shows the counted votes, and answers whether the
whole alliance remains. A correct result can say that the alliance **does not**
survive: verification measures correctness, not a favorable outcome.

This is an original, self-contained `nanoagent.plugin/v0001` plugin. It needs
Python 3.12+, Git, and uv. The tool needs no API key, network access, external
dataset, or LLM.

## Tools

| Tool | Input → output | Purpose |
|---|---|---|
| `resolve_vote` | `CouncilInput` → `CouncilOutput` | Resolve the complete supplied council under the rules below. |

### Tasks

| Task | Runner | Purpose |
|---|---|---|
| `alliance-survival` | `tool`, calling `resolve_vote` | Determine whether every alliance member remains after the vote. |

The tool runner makes local task execution reproducible without model credentials.
RUSH's chat can invoke this task. The plugin does not predict votes or ask an
agent to invent missing ballots.

### Exact voting rules

1. There are **2–24 contestants** and a nonempty alliance drawn from that roster.
   Names are case-sensitive, unique, printable, trimmed strings of 1–80
   characters. Alliance and immunity lists contain no duplicates or unknown names.
2. Every contestant casts **exactly one initial ballot** for another contestant.
   There are no self votes, abstentions, extra votes, or lost votes.
3. **Challenge immunity:** a ballot targeting a challenge-immune contestant is
   invalid. Immune contestants still vote.
4. **Idol protection:** the supplied list describes successful plays already made
   before the count. Initial ballots targeting those contestants are valid ballots
   but are nullified. Protected contestants still vote. Challenge immunity and
   idol protection both last through revotes and rocks; the lists may overlap.
5. The vulnerable contestant with the most counted votes is eliminated. A unique
   leader needs no revote. At least one contestant must be vulnerable.
6. If **all ballots are nullified**, all vulnerable contestants tie at zero.
   Apply the selected tie rule to them. If only one contestant is vulnerable,
   that contestant is eliminated with zero counted votes.
7. The tie policy is one of:

   | `rules.tie_rule` | Initial tie | Continued tie |
   |---|---|---|
   | `priority` | Eliminate the first tied contestant in `priority_order`. | No revote. |
   | `revote_priority` | Every contestant outside the initial tied group votes once, targeting only that group. | Eliminate the first contestant still tied in `priority_order`. |
   | `revote_rocks` | The same revote. | Initially tied contestants and all protected contestants are exempt from rocks. Eliminate the first remaining rock drawer in `priority_order`. |

8. `priority_order` must contain **every contestant exactly once**, even if no tie
   occurs. It is an explicit deterministic elimination order, not a probability
   or an inferred random draw. It selects only among the applicable candidates.
9. `revotes` is required but must be `[]` when there is no initial tie or the
   policy is `priority`. Otherwise it must contain exactly one ballot from each
   initially non-tied contestant, including immune voters. Initially tied
   contestants do not vote. A zero-voter revote is allowed and leaves a tie at
   zero. A rock deadlock with no eligible drawers is **invalid**.
10. Exactly one contestant leaves. `alliance_survives` is true exactly when that
    contestant is **outside the alliance**. Remaining members, all tally rows,
    and deciding candidates are listed in the original `contestants` order.

These are the plugin's complete rules, rather than an attempt to represent every
television season. Idol timing choices, hidden information, strategic voting,
fire-making, final tribal council, and other advantages are outside this task.

### Input example

`tests/scenarios/majority.input.json` contains:

```json
{
  "contestants": ["Ava", "Ben", "Cora", "Drew", "Eli"],
  "alliance": ["Ava", "Ben"],
  "votes": [
    {"voter": "Ava", "target": "Drew"},
    {"voter": "Ben", "target": "Drew"},
    {"voter": "Cora", "target": "Drew"},
    {"voter": "Drew", "target": "Ava"},
    {"voter": "Eli", "target": "Ava"}
  ],
  "challenge_immune": [],
  "idol_protected": [],
  "rules": {
    "tie_rule": "priority",
    "priority_order": ["Ava", "Ben", "Cora", "Drew", "Eli"]
  },
  "revotes": []
}
```

Drew leaves with three votes; Ava has two. The alliance survives.
Adding Drew to `idol_protected` nullifies three votes: Ava leaves and the
alliance no longer survives. Both examples have hand-calculated expected outputs
in `tests/scenarios/`.

### Output and verification

`CouncilOutput` requires all eight fields: `eliminated`, `alliance_survives`,
`alliance_remaining`, `initial_tally`, `nullified_votes`, `revote_tally`,
`resolution`, and `deciding_candidates`. Tallies include zero rows for every
contestant. An unused revote tally is empty. `resolution` is `initial_vote`,
`revote`, `priority`, or `rocks`.

NanoAgent validates types and required fields using `contract.py`.
`verifier/` independently reconstructs the entire expected result from the
input. It does not import the runtime solver or trust its declared winner or
survival flag. All fields must match; verdict scores are 1 for correct and 0
otherwise. Invalid inputs are rejected, and tool failures raise errors.

Only the standard library and declarative contract are used by the verifier.
It has no randomness, environment access, clock, model, network, or file writes.
NanoAgent also checks its imports and calls each verification twice in its
restricted subprocess. No reference tool is needed because all ground truth is
in the task input.

## Layout

```text
survivor-alliance/
├── nanoagent.yaml
├── contract.py
├── README.md
├── LICENSE
├── pyproject.toml
├── uv.lock
├── .gitignore
├── .env                    # comments only; no credentials needed
├── src/plugin/             # MCP server and vote resolver
├── verifier/               # independent input and outcome checks
├── tests/
│   ├── scenarios/          # task fixtures and hand-calculated expectations
│   ├── test_vote.py
│   └── test_verifier.py
├── ui/                     # use NanoAgent's typed result renderer
└── product/                # marketplace description and original torch icon
```

This folder is the entire repository root. It has its own project and lockfile;
it does not import files from the milestone folder or the other four plugins.
The test scenarios are reusable fixtures, not recorded execution evidence.
Keep submission logs and report artifacts outside this repository.

## Develop and run

From this folder:

```bash
uv sync --frozen --extra dev
uv run --frozen pytest
uv run --frozen ruff check .
uv run --frozen ruff format --check .
```

The included lockfile pins the resolved packages and SlimConfig Git revision.
Use `--frozen` when reproducing a run. The source declaration for SlimConfig
follows the NanoAgent template; deliberately updating the lockfile can change
that revision.

Install the NanoAgent CLI separately. This plugin was validated against
NanoAgent 0.7.0, repository commit
`57714f62880eee11319765854e398af61e67b7b7`:

```bash
uv tool install 'nanoagent @ git+https://github.com/RUSH-LAB/nanoagent.git@57714f62880eee11319765854e398af61e67b7b7#subdirectory=nanoagent'
nanoagent plugin inspect .
```

To run the example through the real MCP runtime and verifier, save the following
as a YAML file **outside this folder**, replacing the two paths with absolute
paths on your computer:

```yaml
_ > nanoagent.cli.plugin.PluginRunConfig:
plugin: /absolute/path/to/survivor-alliance
task: alliance-survival
arguments: /absolute/path/to/survivor-alliance/tests/scenarios/majority.input.json
inputs: []
timeout: 60.0
```

Then run it with a new evidence folder:

```bash
nanoagent plugin run config=/absolute/path/to/run.yaml home=/absolute/path/to/evidence/majority
nanoagent plugin pack . /absolute/path/to/evidence/survivor-alliance.tar.gz
```

The task run creates `result.json`, `verdict.json`, `run.log`, and its other
standard NanoAgent run files. Keep those outside the plugin repository for the
milestone report.

### Separate Git repository

From this folder, initialize a repository if it has not already been initialized:

```bash
git init -b main
git add .
git commit -m "Add Survivor alliance survival plugin"
```

The GitHub repository for this plugin is
[chengostalgic/survivor-alliance-voting](https://github.com/chengostalgic/survivor-alliance-voting).
If `origin` is not already configured, connect it with:

```bash
git remote add origin https://github.com/chengostalgic/survivor-alliance-voting.git
```

Then push the committed plugin:

```bash
git push -u origin main
```

Publish that repository through the RUSH Lab marketplace and retain the real
publication result in the report evidence. Local validation alone does not
establish marketplace publication.
