import { dataTable, disclosure, h, statusPill } from "./kit/components.js";

const advantageNames = { idol: "Idol", extra_vote: "Extra vote", vote_block: "Vote block" };

const describePlay = (play, inventory) => {
  const item = inventory.find((entry) => entry.id === play.item_id);
  const effect = item.kind === "idol"
    ? "protect " + play.target
    : item.kind === "extra_vote"
      ? "cast an extra vote against " + play.target
      : "block " + play.target + "'s original ballot";
  return item.owner + " uses " + item.id + " to " + effect;
};

export default {
  ScenarioOutput: (value, { verdict }) => {
    if (verdict?.valid === false) {
      return h("section", { class: "scenario" }, statusPill("Verification failed", "bad"), h("p", { text: verdict.message }));
    }
    const council = value.scenario.council;
    const outcome = value.outcome;
    const labels = {
      not_specified: outcome.alliance_survives ? "Every alliance member stays" : "An alliance member goes home",
      you_go_home: "You go home in this scenario",
      ally_goes_home: "An ally goes home in this scenario",
      alliance_safe: "You and your whole alliance stay",
    };
    const names = (members) => members.length ? members.join(", ") : "Nobody";
    return h("section", { class: "scenario" },
      h("p", { class: "muted", text: "Under your assumed votes and plays" }),
      statusPill(labels[value.personal_outcome], outcome.alliance_survives ? "ok" : "warn", { icon: true }),
      h("p", { class: "baseline", text: outcome.eliminated + " is eliminated under these assumptions." }),
      h("p", { text: outcome.nullified_votes + " cast votes nullified. Whole alliance survives: " + (outcome.alliance_survives ? "Yes" : "No") + "." }),
      dataTable({ columns: [
        { key: "contestant", label: "Contestant", primary: true },
        { key: "votes", label: "Counted initial votes", numeric: true },
      ], rows: outcome.initial_tally, caption: "Votes after the specified plays" }).element,
      outcome.revote_tally.length ? dataTable({ columns: [
        { key: "contestant", label: "Contestant", primary: true },
        { key: "votes", label: "Revote votes", numeric: true },
      ], rows: outcome.revote_tally, caption: "Supplied revote" }).element : null,
      h("p", { text: "Resolution: " + outcome.resolution + ". Final candidates: " + names(outcome.deciding_candidates) + "." }),
      disclosure({ summary: "Check the assumed scenario", open: true },
        h("p", { text: "Contestants: " + names(council.contestants) }),
        h("p", { text: "Alliance: " + names(council.alliance) + ". You: " + (value.scenario.perspective ?? "Not identified") }),
        h("p", { text: "Challenge immunity: " + names(council.challenge_immune) }),
        dataTable({ columns: [{ key: "voter", label: "Voter" }, { key: "target", label: "Assumed ordinary vote" }], rows: council.votes, caption: "Ordinary ballots before blocks and extra votes" }).element,
        value.scenario.plays.length ? dataTable({ columns: [
          { key: "id", label: "Played item" }, { key: "owner", label: "Played by" },
          { key: "kind", label: "Advantage" }, { key: "target", label: "Recipient or target" },
        ], rows: value.scenario.plays.map((play) => ({ ...play, kind: advantageNames[play.kind] })), caption: "Only these items are played" }).element
          : h("p", { text: "No idols or advantages are played." }),
        h("p", { text: "Idol recipients: " + names(value.idol_recipients) + ". Blocked ordinary voters: " + names(value.blocked_voters) }),
        h("p", { text: "Tie rule: " + council.rules.tie_rule + ". Supplied elimination priority: " + council.rules.priority_order.join(", ") }),
        h("p", { text: "Blocks and extra votes apply to the initial round only; idols last through revotes and rocks in this declared ruleset." }),
      ),
      h("p", { class: "muted", text: "Verification checks the calculation for these supplied facts. It does not establish that people will actually vote or play items this way, or that the chat interpreted your description correctly." }),
    );
  },
  RescueOutput: (value, { verdict }) => {
    if (verdict?.valid === false) {
      return h("section", { class: "rescue" },
        statusPill("Verification failed", "bad"),
        h("p", { text: verdict.message }),
      );
    }
    const labels = {
      already_safe: ["Your alliance already survives", "ok"],
      rescuable: ["A single vote can save your alliance", "ok"],
      impossible: ["No single-vote rescue", "warn"],
    };
    const [label, tone] = labels[value.status];
    const council = value.council;
    const moves = value.suggestions.map((move) => ({
      voter: move.voter,
      from: move.from_target,
      to: move.to_target,
      eliminated: move.outcome.eliminated,
    }));
    const empty = value.status === "already_safe"
      ? "No change is needed; every alliance member is already safe."
      : "No legal vote change by one alliance member saves everyone under these rules.";
    const names = (members) => members.length ? members.join(", ") : "Nobody";

    return h("section", { class: "rescue" },
      h("p", { class: "muted", text: "Conditional on the supplied votes, protection, and tie rules." }),
      statusPill(label, tone, { icon: true }),
      h("p", { class: "baseline", text: "Before changes: " + value.baseline.eliminated + " is eliminated." }),
      h("p", { class: "muted", text: value.tested_changes + " legal changes checked; " + value.saving_change_count + " save the whole alliance." }),
      moves.length
        ? dataTable({
            columns: [
              { key: "voter", label: "Who changes", primary: true },
              { key: "from", label: "Original target" },
              { key: "to", label: "New target" },
              { key: "eliminated", label: "Who leaves" },
            ],
            rows: moves,
            caption: "Saving single-vote changes",
          }).element
        : h("p", { text: empty }),
      moves.length
        ? h("p", { class: "muted", text: "Showing " + moves.length + " of " + value.saving_change_count + " saving moves, in roster order." })
        : null,
      disclosure({ summary: "Check the interpreted scenario", open: true },
        h("p", { text: "Contestants: " + names(council.contestants) }),
        h("p", { text: "Alliance: " + names(council.alliance) }),
        h("p", { text: "Challenge immunity: " + names(council.challenge_immune) }),
        h("p", { text: "Idol protection: " + names(council.idol_protected) }),
        h("p", { text: "Tie priority (first eligible name leaves): " + council.rules.priority_order.join(", ") }),
        dataTable({
          columns: [
            { key: "voter", label: "Voter", primary: true },
            { key: "target", label: "Target" },
          ],
          rows: council.votes,
          caption: "Interpreted initial ballots",
        }).element,
      ),
      disclosure({ summary: "Baseline vote totals" },
        dataTable({
          columns: [
            { key: "contestant", label: "Contestant", primary: true },
            { key: "votes", label: "Counted votes", numeric: true },
          ],
          rows: value.baseline.initial_tally,
          caption: "Baseline counted votes",
        }).element,
      ),
      disclosure({ summary: "Full verified outcomes" },
        h("pre", { text: JSON.stringify({ baseline: value.baseline, suggestions: value.suggestions }, null, 2) }),
      ),
    );
  },
  AdvantageOutput: (value, { verdict }) => {
    if (verdict?.valid === false) {
      return h("section", { class: "advantages" }, statusPill("Verification failed", "bad"), h("p", { text: verdict.message }));
    }
    const council = value.scenario.council;
    const inventory = value.scenario.inventory;
    const labels = {
      hold: ["Keep your remaining items", "ok"],
      play: ["An advantage play saves the alliance", "ok"],
      no_saving_plan: ["No saving plan using up to two items", "warn"],
    };
    const [label, tone] = labels[value.decision];
    const minimum = value.minimum_items_needed;
    const needed = minimum === 0 ? "No additional item is needed."
      : minimum === null ? "No saving plan was found using zero, one, or two items."
        : minimum === 1 ? "One item can save everyone." : "Two items are needed to save everyone.";
    const choices = value.single_plays.map((row) => ({
      item: row.play.item_id,
      owner: row.owner,
      kind: advantageNames[row.kind],
      target: row.play.target,
      eliminated: row.eliminated ?? "—",
      safe: row.alliance_survives === null ? "Invalid play" : row.alliance_survives ? "Yes" : "No",
      tally: row.vote_tally.filter((entry) => entry.votes > 0).map((entry) => entry.contestant + ": " + entry.votes).join(", ") || "No counted votes",
      nullified: row.nullified_votes ?? "—",
      reason: row.reason,
    }));
    const recommendations = value.recommendations.map((plan) => ({
      play: plan.plays.length ? plan.plays.map((use) => describePlay(use, inventory)).join("; ") : "Hold all remaining items",
      items: plan.plays.length,
      eliminated: plan.outcome.eliminated,
      safe: plan.outcome.alliance_survives ? "Yes" : "No",
    }));
    const names = (members) => members.length ? members.join(", ") : "Nobody";
    return h("section", { class: "advantages" },
      h("p", { class: "muted", text: "Conditional on these assumed votes and the declared alternative plays." }),
      statusPill(label, tone, { icon: true }),
      h("p", { class: "baseline", text: "No optional play: " + value.baseline.eliminated + " is eliminated. Alliance survives: " + (value.baseline.alliance_survives ? "Yes" : "No") + "." }),
      h("p", { text: needed }),
      h("p", { class: "muted", text: value.plans_checked + " plans checked, including no play, every single play, and every pair. " + value.saving_plan_count + " keep the whole alliance safe." }),
      recommendations.length ? dataTable({
        columns: [
          { key: "play", label: "Recommended play", primary: true },
          { key: "items", label: "Items used", numeric: true },
          { key: "eliminated", label: "Who leaves" },
          { key: "safe", label: "Alliance survives" },
        ],
        rows: recommendations,
        caption: "Plans using the fewest items",
      }).element : null,
      recommendations.length ? h("p", { class: "muted", text: value.minimal_saving_plan_count + " plans use the fewest items; showing " + recommendations.length + ". Items are counted equally, without assuming their future strategic value." }) : null,
      choices.length ? disclosure({ summary: "Compare every single play", open: true }, dataTable({
        columns: [
          { key: "item", label: "Item", primary: true },
          { key: "owner", label: "Owner" },
          { key: "kind", label: "Advantage" },
          { key: "target", label: "Target" },
          { key: "eliminated", label: "Who leaves" },
          { key: "safe", label: "Alliance survives" },
          { key: "tally", label: "Counted votes" },
          { key: "nullified", label: "Votes nullified", numeric: true },
          { key: "reason", label: "Why invalid" },
        ], rows: choices, caption: "All single-item outcomes", limit: 12,
        filterPlaceholder: "Find an item, owner, or target",
      }).element) : h("p", { text: "No optional items are available." }),
      disclosure({ summary: "How these advantages work" },
        h("ul", {},
          h("li", { text: "Idol: protects its recipient before the tally. Votes against them do not count, including extra votes." }),
          h("li", { text: "Extra vote: adds one ballot from its owner. The original ballot is unchanged." }),
          h("li", { text: "Vote block: removes the target's original ballot. It does not remove an extra ballot or prevent an idol play. Blocking the same person twice removes the original ballot only once." }),
        ),
        h("p", { text: "These are this planner's explicit rules, rather than every television-season variant. Other voters' intended ballots stay fixed. The search uses at most two of the three available items, and ties follow your supplied priority order." }),
      ),
      disclosure({ summary: "Check the interpreted council and inventory" },
        h("p", { text: "Contestants: " + names(council.contestants) }),
        h("p", { text: "Alliance: " + names(council.alliance) }),
        h("p", { text: "Challenge immunity: " + names(council.challenge_immune) }),
        h("p", { text: "Idols already played: " + names(council.idol_protected) }),
        h("p", { text: "Tie priority (first tied name leaves): " + council.rules.priority_order.join(", ") }),
        dataTable({ columns: [{ key: "voter", label: "Voter" }, { key: "target", label: "Intended ordinary vote" }], rows: council.votes, caption: "Known intended ballots" }).element,
        dataTable({ columns: [
          { key: "id", label: "Item" }, { key: "owner", label: "Owner" },
          { key: "kind", label: "Advantage" }, { key: "targets", label: "Allowed targets" },
        ], rows: inventory.map((item) => ({ id: item.id, owner: item.owner, kind: advantageNames[item.kind], targets: item.allowed_targets.join(", ") })), caption: "Available inventory", empty: "No items available" }).element,
      ),
      disclosure({ summary: "Vote totals after recommended plays" },
        value.recommendations.map((plan) => h("div", { class: "plan-detail" },
          h("p", { text: plan.plays.length ? plan.plays.map((use) => describePlay(use, inventory)).join("; ") : "Hold all remaining items" }),
          h("p", { text: plan.outcome.nullified_votes + " votes nullified; " + plan.outcome.eliminated + " leaves." }),
          dataTable({ columns: [{ key: "contestant", label: "Contestant" }, { key: "votes", label: "Counted votes", numeric: true }], rows: plan.outcome.initial_tally, caption: "Votes after this plan" }).element,
        )),
      ),
    );
  },
};
