import { dataTable, disclosure, h, statusPill } from "./kit/components.js";

export default {
  TribalScenarioOutput: (value, { verdict }) => {
    if (verdict?.valid === false) return h("section", { class: "scenario" }, statusPill("Verification failed", "bad"), h("p", { text: verdict.message }));
    const outcome = value.outcome;
    const council = value.scenario.council;
    const names = (values) => values.length ? values.join(", ") : "Not specified";
    const labels = {
      complete: outcome.eliminated + " goes home in this scenario",
      revote_required: "Revote required",
      deadlock: "Deadlocked revote: decision or rocks",
      fire_required: "Fire-making result pending",
    };
    const personal = {
      you_go_home: "You go home under these assumptions.",
      ally_goes_home: "An ally goes home under these assumptions.",
      alliance_safe: "You and your whole alliance stay under these assumptions.",
      awaiting_result: "Your outcome is unresolved until the missing facts are supplied.",
      not_specified: "",
    };
    return h("section", { class: "scenario" },
      h("p", { class: "muted", text: "Under the stated votes and plays; ballot order has no effect." }),
      statusPill(labels[outcome.stage], outcome.stage === "complete" && outcome.alliance_survives ? "ok" : "warn"),
      personal[value.personal_outcome] ? h("p", { text: personal[value.personal_outcome] }) : null,
      outcome.alliance_survives !== null ? h("p", { text: "Whole alliance survives: " + (outcome.alliance_survives ? "Yes" : "No") }) : null,
      outcome.initial_tally.length ? dataTable({ columns: [
        { key: "contestant", label: "Contestant" }, { key: "votes", label: "Counted initial votes", numeric: true },
      ], rows: outcome.initial_tally, caption: "After the stated advantage plays" }).element : null,
      outcome.initial_tally.length ? h("p", { text: outcome.nullified_votes + " cast votes nullified." }) : null,
      outcome.tied_contestants.length ? h("p", { text: "Initially tied contestants (do not revote): " + names(outcome.tied_contestants) }) : null,
      outcome.revote_voters.length ? h("p", { text: "Eligible revoters: " + names(outcome.revote_voters) }) : null,
      outcome.revote_tally.length ? dataTable({ columns: [
        { key: "contestant", label: "Contestant" }, { key: "votes", label: "Revote votes", numeric: true },
      ], rows: outcome.revote_tally, caption: "Supplied revote" }).element : null,
      outcome.stage === "deadlock" ? h("p", { text: "A unanimous decision can resolve the deadlock. Otherwise eligible rock drawers are: " + names(outcome.rock_drawers) + ". No random loser has been chosen." }) : null,
      outcome.fire_contestants.length ? h("p", { text: "Fire-making contestants: " + names(outcome.fire_contestants) }) : null,
      outcome.needed_facts.length ? h("p", { text: "Still needed: " + outcome.needed_facts.join(", ") }) : null,
      disclosure({ summary: "Check the assumed scenario", open: true },
        h("p", { text: "Format: " + (council.format ?? "standard") + ". Contestants: " + names(council.contestants) }),
        h("p", { text: "Alliance: " + names(council.alliance) + ". Challenge immunity: " + names(council.challenge_immune) }),
        council.votes.length ? dataTable({ columns: [{ key: "voter", label: "Voter" }, { key: "target", label: "Assumed ordinary vote" }], rows: council.votes, caption: "Votes before advantage effects" }).element : h("p", { text: "This forced-fire format has no vote." }),
        value.scenario.plays.length ? dataTable({ columns: [
          { key: "owner", label: "Played by" }, { key: "kind", label: "Advantage" }, { key: "target", label: "Recipient or target" },
        ], rows: value.scenario.plays, caption: "Assumed item plays" }).element : null,
        h("p", { text: "Protected idol recipients: " + names(value.idol_recipients) }),
      ),
      h("p", { class: "muted", text: "Verification checks the stated scenario. Loyalty, votes, item plays, and any supplied rock or fire result remain assumptions. A pending result is valid; it does not predict randomness or challenge ability." }),
    );
  },
};
