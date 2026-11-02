# Survivor Alliance

Does **every member of your alliance** survive one Survivor-style tribal council?
If they do not, can **one changed alliance vote** save everyone?
Or do you need to **play an idol, use a vote advantage, or save your items**?

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
| `find_rescue` | `CouncilInput` → `RescueOutput` | Check every legal initial-vote change by one alliance member and find saving moves. |
| `plan_advantages` | `AdvantageInput` → `AdvantageOutput` | Compare holding items, idols, extra votes, and vote blocks; find plays using the fewest items. |

### Tasks

| Task | Runner | Purpose |
|---|---|---|
| `alliance-survival` | `tool`, calling `resolve_vote` | Determine whether every alliance member remains after the vote. |
| `single-vote-rescue` | `tool`, calling `find_rescue` | Find whether a single alliance ballot can save everyone, using an explicit priority tie rule. |
| `advantage-planner` | `tool`, calling `plan_advantages` | Decide whether an optional advantage is needed and compare its resulting vote outcomes. |

The tool runner makes local task execution reproducible without model credentials.
RUSH's chat can invoke this task. The plugin does not predict votes or ask an
agent to invent missing ballots.

### Describe the situation in ordinary chat

You do not have to write JSON. RUSH's chat model converts your description into
the typed task input. For example, paste this into the installed plugin's chat:

```text
Can one of us changing our vote save our alliance?

The contestants are Ava, Ben, Cora, Drew, and Eli.
My alliance is Ava and Ben.
Ava and Eli vote for Drew. Ben, Cora, and Drew vote for Ava.
Nobody has challenge immunity, and no idols are played.
Resolve ties without a revote: the first tied contestant in this order leaves:
Ava, Ben, Cora, Drew, Eli.
```

The baseline eliminates Ava, with three votes against Ava and two against Drew.
The search checks six legal changes and finds one saving move: **Ben changes his
vote from Ava to Drew**. Drew then leaves 3–2, and both alliance members remain.

The rescue result displays the interpreted roster, alliance, ballots, immunity,
and priority order. Check these facts against what you meant. If a fact or tie
rule is missing, the task descriptions tell the chat model to ask rather than
invent it. The verifier checks the typed facts, not the meaning of arbitrary
English; language interpretation is performed by the chat model and can be
mistaken. RUSH chat uses its configured model/key; the local Python tasks and
their tests make no model calls.

Follow up naturally, for example: "What if Drew plays an idol?" or "Ben's vote
was actually for Drew; check the council again." State uncertain votes as separate
what-if cases; the solver resolves explicit ballots rather than predicting people.

### Single-vote rescue rules

The original council rules below apply. For this strategic task:

1. `tie_rule` must be `priority`, with the user's explicit `priority_order`, and
   `revotes` must be empty. A changed initial vote could create a different revote
   requiring new ballots, so this search requires a complete deterministic tie
   policy instead of guessing those ballots.
2. Resolve the baseline first. If everyone is already safe, return
   `status: already_safe`, zero tested changes, zero saving changes, and no
   suggestions: no rescue is needed.
3. Otherwise, independently try every legal alternative target for every
   **alliance member's** initial ballot. Change exactly that ballot. Keep the
   other ballots, alliance, immunity, and priority order fixed. Exclude self
   votes, challenge-immune targets, and the ballot's original target. A vote
   against an idol-protected contestant is legal and can be nullified.
4. A move saves the alliance exactly when its new outcome eliminates no alliance
   member. Return `rescuable` if at least one exists, or `impossible` if none does.
   The latter means no single-vote rescue under these supplied rules.
5. `tested_changes` counts every legal alternative, and `saving_change_count`
   counts every saving alternative. Return the first **five** saving moves in
   roster voter/target order, each with its complete council outcome. These are
   verified moves, not a ranking of strategic preferences or probabilities.

`RescueOutput` includes `council` (the interpreted facts), `baseline`, `status`,
`tested_changes`, `saving_change_count`, and `suggestions`. Its verifier runs its
own exhaustive search; it rejects false claims that no rescue exists, omitted or
invented moves, altered outcomes, incorrect counts, and reordered suggestions.

### Should you play an advantage?

The planner answers: **given these intended votes and this available inventory,
do we need to spend anything to keep the whole alliance safe?** It compares no
optional play, every allowed single-item play, and every allowed two-item
combination. It counts all saving plans and shows the first five that use the
fewest items. Every single-item alternative includes its vote totals, eliminated
contestant, alliance result, and nullified votes, including wasteful or harmful plays.

Try this in chat:

```text
Should we play our idols, and who should we protect?

The cast is Ava, Ben, Cora, Drew, Eli, Finn, and Gia. Our alliance is Ava and Ben.
Ava and Ben vote for Cora. Cora, Drew, and Eli vote for Ava.
Finn and Gia vote for Ben. Nobody has challenge immunity, and no idols have been played.

Ava has one usable idol named Ava-idol. Ben has one usable idol named Ben-idol.
For this comparison, either idol may target Ava or Ben.
No revotes: ties eliminate the first tied contestant in this order:
Ava, Ben, Cora, Drew, Eli, Finn, Gia.

Compare holding both idols with using one or two. Does the whole alliance survive?
```

Ava initially leaves, with votes 3–2–2 against Ava, Ben, and Cora. An idol on Ava
alone shifts elimination to **Ben**, so it does not save the whole alliance.
An idol on Ben alone still eliminates Ava. Protecting both allies nullifies five
votes and eliminates **Cora**. The verified minimum is **two items**, with two
equivalent ways to assign the two idols to the two allies.

#### Advantage guide: this planner's explicit rules

| Item | Effect and timing in this model | Important interactions |
|---|---|---|
| **Idol** | Protect its selected recipient before counting ballots. All ballots against the recipient are nullified. | Includes extra votes. It can protect another contestant. Two idols on one person do not protect a second person. |
| **Extra vote** | Add one ballot from the item's owner against its selected legal target. | Does not change the owner's ordinary ballot. It can be nullified by an idol. Multiple distinct items may add multiple ballots. |
| **Vote block** | Remove the selected contestant's ordinary ballot before the tally. | Does not remove an extra ballot, prevent an idol play, or remove a ballot twice if two blocks target the same voter. A challenge-immune contestant's vote can be blocked. |

These declared rules are a reproducible Survivor-inspired variant. Actual
advantage instructions and interactions vary; this plugin does not claim to
implement every television season's rules.

#### Inventory, search limits, and scoring

- `AdvantageInput` contains the `council` and an `inventory` of **0–3 usable,
  alliance-owned items**. Each item has a unique `id`, `owner`, `kind` (`idol`,
  `extra_vote`, or `vote_block`), and a nonempty `allowed_targets` list. Each item
  may be spent at most once. Different items can have the same owner.
- Target restrictions are explicit. Without a stated special restriction, a
  normal idol may target any contestant; an extra vote may target anyone except
  its owner or a challenge-immune contestant; a vote block may target anyone
  except its owner. Target lists may narrow the options the user wants compared.
- Held idols are **inventory**, not protection already in effect. Only idols
  already played belong in `council.idol_protected`. List only items usable in
  this council; expiry, acquisition, and future ownership are outside the model.
- The council must use `priority` ties with no revotes. Intended ordinary ballots,
  challenge immunity, existing idol protection, and alliance membership stay fixed.
  Other people do not change their votes in response to a proposed play.
- Compare zero, one, or **two distinct inventory items** per plan. All allowed
  target combinations are checked, in inventory/roster order. At the largest
  supported roster (24), three idols with every target allowed produce **1,801**
  plans. No probabilities, random draws, or model judgement enter that search.
- `decision: hold` and `minimum_items_needed: 0` mean no *additional* item is
  needed. The planner still shows single plays that would waste an item or harm
  the alliance. `play` reports a minimum of one or two. `no_saving_plan` and a null
  minimum mean none succeeds **within the two-item search**, not that three items
  or a different strategy could never help.
- The result includes total plans checked, all saving plans counted, the number
  using the fewest items, and up to five complete recommendations. Every single
  play is shown, not just the successful ones. A plan that protects every
  contestant has no defined elimination under this ruleset; it is displayed as
  invalid with an explanation and is never recommended.
- All items have equal cost for this objective. A one-item idol plan and a
  one-item vote-block plan are tied; the solver does not invent a future value for
  either. Compare the alternatives before deciding what to conserve.

`AdvantageOutput` echoes the interpreted scenario and inventory, baseline,
decision, minimum items, complete plan counts, recommendations, and all
single-play comparisons. The verifier independently rebuilds the weighted
ballots and enumerates the full search, checking every returned field. A correct
"hold" or "no saving plan" result passes just as a correct recommendation does.

### Ordinary council rules before optional advantage plays

1. There are **2–24 contestants** and a nonempty alliance drawn from that roster.
   Names are case-sensitive, unique, printable, trimmed strings of 1–80
   characters. Alliance and immunity lists contain no duplicates or unknown names.
2. Every contestant casts **exactly one initial ballot** for another contestant.
   There are no self votes or abstentions in these intended ordinary ballots.
   The advantage planner applies optional extra ballots and vote blocks afterward.
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
television season. Hidden information, predicting votes, fire-making, final tribal
council, and advantage types beyond the three explicitly supported are outside
this model.

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
├── src/plugin/             # MCP server, vote resolver, and rescue search
├── verifier/               # independent input and outcome checks
├── tests/
│   ├── scenarios/          # task fixtures and hand-calculated expectations
│   ├── rescues/            # hand-calculated strategic scenarios
│   ├── advantages/         # hand-calculated idol/extra-vote/block cases
│   ├── test_vote.py
│   ├── test_rescue.py
│   ├── test_advantages.py
│   ├── test_ui.py
│   └── test_verifier.py
├── ui/                     # rescue/planning cards; schema renderer for basic councils
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
uv run --frozen --extra dev pytest
uv run --frozen --extra dev ruff check .
uv run --frozen --extra dev ruff format --check .
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

To test the rescue task, use `task: single-vote-rescue` and point `arguments` at
`tests/rescues/save-one.input.json` in a new run config. Its hand-calculated
expected output is alongside it. Neither task requires an API key when run this way.

For the advantage task, use `task: advantage-planner` and
`tests/advantages/two-idols-split-vote.input.json`. It also runs without a model
key locally; ordinary-language chat uses RUSH's configured model. All three
tasks have hand-calculated fixtures and deterministic verifiers.

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

Version 0.2.0 adds the rescue task and its result card. After committing and
pushing changes, republish this repository through the marketplace and install
the updated version to use them. An existing 0.1.0 installation keeps its old
task set until it is updated.

Version 0.3.0 adds `advantage-planner`, its advantage guide, and before/after
comparisons. Republish and install that version to use the new task.
