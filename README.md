# Survivor Alliance

**Given these assumed votes and item plays, who goes home?**

Evaluate one fully specified hypothetical Survivor-style council. Supply who is
voting for whom, every idol and advantage being played, challenge immunity, and
the council format when at the final four. The plugin calculates who leaves, whether it is you or an
ally, and whether every alliance member stays. Describe it in ordinary chat;
you do not need to prepare JSON.

**The major limitation:** all votes and plays must be known *within the guessed
scenario*. Actual players may vote or act differently. A valid verifier verdict
means the calculation follows the supplied assumptions and declared rules. It
does not certify that the scenario will happen or that the chat model understood
your prose correctly. A correct result saying **you go home** or **an ally goes
home** passes just as a correct safe result does.

This is an original, self-contained `nanoagent.plugin/v0001` plugin. It needs
Python 3.12+, Git, and uv. The tool needs no API key, network access, external
dataset, or LLM.

## Tools

| Tool | Input → output | Purpose |
|---|---|---|
| `resolve_tribal` | `TribalScenarioInput` → `TribalScenarioOutput` | Main evaluator: vote, revote, deadlock/rocks, or final-four fire; unresolved results remain pending. |

### Tasks

| Task | Runner | Purpose |
|---|---|---|
| `scenario-outcome` | `tool`, calling `resolve_tribal` | Default: supported Survivor vote/revote/rocks or final-four formats, without any priority order. |

The tool runner makes local task execution reproducible without model credentials.
RUSH's chat can invoke this task. The plugin does not predict votes or ask an
agent to invent missing ballots.

### Evaluate a guessed scenario in ordinary chat

Paste this into the updated plugin's chat:

```text
Evaluate this hypothetical council. I am John.
The contestants are John, Esther, Cora, Drew, and Eli.
Our alliance is John and Esther.
Assume John and Esther vote for Drew. Cora, Drew, and Eli vote for John.
Nobody has challenge immunity.
Esther plays her idol, Esther-idol, on John. No other idols or advantages are played.
Under exactly these assumptions, who goes home? Does our alliance survive?
```

John's three votes are nullified. Drew leaves with two counted votes, so John
and Esther both stay. Esther owns the idol; **John is the protected recipient**.
If Esther instead keeps the idol and nobody plays anything, John goes home 3–2.
Both are correct calculations, and both pass verification.

**Vote order never matters.** The input has no custom tiebreak policy. Listing ballots or contestants in a different order cannot
choose a different loser. Roster order controls display only.

The main task follows these stages:

1. Count the ordinary votes after the stated plays. A unique leader leaves.
2. On a tie, **tied contestants do not revote**. Other contestants vote only for
   those tied. If revote ballots were not supplied, return `revote_required`
   and list eligible revoters; do not invent their decisions.
3. A unique revote leader leaves. After a continued standard deadlock, a stated
   unanimous decision can eliminate a still-tied contestant. Otherwise the
   non-tied, non-protected contestants are eligible for rocks. A missing
   decision/draw result returns `deadlock` with the eligible drawers and a null
   elimination. If the user explicitly assumes a rock loser, validate eligibility
   and use that supplied result. Never predict a random draw.
4. The **final four is a separate format**. `final_four_vote` uses voting and a
   revote, followed by fire between two still-tied contestants. `final_four_fire`
   is the forced-fire format: no vote, with a supplied pair making fire. A missing
   pair or winner returns `fire_required`; only an explicitly supplied actual or
   assumed winner resolves the elimination. Four contestants at an ordinary
   tribe do not automatically mean the final four.

The standard deadlock procedure is illustrated in an [official Paramount+
recap](https://www.paramountplus.com/sneak-peak/survivor-season-51-episode-5-recap/).
CBS describes the immunity winner's choice of finalists and fire competitors in
its [final-four challenge clip](https://www.cbs.com/shows/video/ALVE01KS8N4ZMZE1SS4TX0JEJDFY6A/).
The plugin explicitly supports the formats above; it does not infer every
season's rules merely from roster size.

For a final-four example, say:

```text
We are at the final four using the forced fire-making format, not a vote.
The contestants are Ava, Ben, Cora, and Drew. I am Ava; Cora is my ally.
Ben and Cora make fire. Assume Ben wins. No advantages are played.
```

The result eliminates Cora by fire, so an ally goes home. Omitting "Assume Ben
wins" leaves the result pending; a verifier can confirm that the correct answer
is unresolved without pretending to know challenge performance.

#### Main input and verification

`TribalScenarioInput` has `council`, `plays`, `perspective`, and
`resolution_facts`. The chat model constructs these internally. The council has
`contestants`, `alliance`, ordinary `votes`, `challenge_immune`, `format` (null
means standard), and `revotes` ([] when unknown/unused). Every played item has
an `id`, `owner`, `kind`, and `target`; held items have no effect. The owner can
be an opponent. A perspective is a named alliance member, or null if unidentified.

Use `resolution_facts: null` unless a later decision/result was stated. Its
fields are `consensus_eliminated`, `rock_draw_loser`, `fire_participants` (two
names or []), and `fire_winner`; unknown names are null. Supplying a random
result is an additional scenario assumption, not an ordering of ballots.

`TribalScenarioOutput` echoes the scenario, complete tallies, nullified votes,
protected recipients, removed ordinary voters, and added ballots. Its `outcome`
contains `stage`, nullable `eliminated`, nullable `alliance_survives`, nullable
`alliance_remaining`, `initial_tally`, `nullified_votes`, `revote_tally`, nullable
`resolution`, `tied_contestants`, `revote_voters`, `rock_drawers`,
`fire_contestants`, and `needed_facts`. Personal outcomes include
`awaiting_result` alongside the definite safe/losing results.

The independent verifier checks every returned field. Correct pending and losing
results receive a valid score of 1. The runtime never rolls dice or guesses fire
winners. It counts with a Counter; the verifier independently scans every
candidate's ballots. Neither imports the other's solver.

The major behavioral limitation still applies: alliance labels, votes, item
plays, and any supplied draw/challenge result are assumed to happen exactly as
described. The verifier certifies conditional arithmetic and stage handling,
not loyalty, future behavior, or arbitrary prose interpretation. The result card
shows the interpreted facts for checking.

The advantage interactions remain an explicit simplified variant: idols protect
through revotes/rocks; extra votes and vote blocks affect the initial round only;
a block removes only the ordinary ballot and does not cancel a separate extra
vote. Supported final-four formats do not allow advantage plays. Special
vote-loss/extra-vote revote exceptions, arbitrary season-specific timing,
fire-making skill prediction, and probabilities are outside this model.

## Layout

```text
survivor-alliance/
├── nanoagent.yaml
├── contract.py
├── README.md
├── LICENSE
├── pyproject.toml
├── uv.lock
├── src/plugin/             # MCP server, tribal evaluator, ballot helpers
├── verifier/               # independent tribal replay and validation helpers
├── tests/
│   ├── tribal/             # hand-calculated standard council/fire fixtures
│   ├── test_verifier.py
│   └── test_ui.py
├── ui/                     # tribal scenario result card
└── product/                # marketplace metadata and torch icon
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
task: scenario-outcome
arguments: /absolute/path/to/survivor-alliance/tests/tribal/idol-on-other.input.json
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

Version 0.5.1 removes the obsolete custom contracts, tools, and artificial tie
policies. Only the standard tribal-council evaluator is exposed. Push and
republish the new version to update RUSH.
