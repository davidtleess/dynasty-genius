import { useEffect, useState } from "react";

import "./ModelScoreboard.css";

// The model's record against real outcomes, in the order a manager asks:
//   1. Does it beat the market? (the edge question — currently unanswerable for QB)
//   2. Does it beat carrying last year's points forward? (answered, with a caveat that
//      travels with the number)
// Descriptive only: no verdicts, no recommended action, decision_supported stays false.
// The contrast unit is Spearman rank-correlation, NEVER fantasy points — the surface
// states the unit next to every number so it cannot be misread as points per game.

type Effect = {
  value: number;
  ci_low: number | null;
  ci_high: number | null;
  unit: string;
  adjusted_p: number | null;
  evaluable_folds: number | null;
  total_folds: number | null;
};

type Scoreboard = {
  generated_at: string;
  study_label: string;
  market_question: {
    position: string;
    state: "unanswered" | "answered";
    headline: string;
    why: string;
    what_would_answer_it: string;
    evaluable_folds: number;
    total_folds: number;
    effect_direction_note: string;
  };
  baseline_question: {
    position: string;
    headline: string;
    effect: Effect;
    materiality_floor: number;
    below_materiality_floor: boolean;
    materiality_note: string;
    counterweight_headline: string;
    counterweight_effect: Effect;
  };
  position_scope: { studied: string[]; unstudied: string[]; note: string };
  live: {
    state: "not_started" | "accruing";
    headline: string;
    weeks_graded: number;
    predictions_declared: number | null;
    predictions_graded: number | null;
    rank_eligible: number | null;
    rank_metrics_available: boolean;
    rank_availability_note: string;
  };
};

type State =
  | { status: "loading" }
  | { status: "ready"; data: Scoreboard }
  | { status: "unavailable" };

const signed = (n: number) => `${n >= 0 ? "+" : "−"}${Math.abs(n).toFixed(3)}`;

export function ModelScoreboard() {
  const [state, setState] = useState<State>({ status: "loading" });

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const res = await fetch("/api/model-scoreboard");
        if (!res.ok) {
          if (active) setState({ status: "unavailable" });
          return;
        }
        const data = (await res.json()) as Scoreboard;
        // Shape check before render. Without it, any payload that is not this
        // contract — a schema drift, a different endpoint's body, a proxy error
        // page — reaches the destructure below and throws, taking the whole
        // surface down instead of degrading to the unavailable state.
        if (
          !data?.market_question ||
          !data?.baseline_question?.effect ||
          !data?.position_scope ||
          !data?.live
        ) {
          if (active) setState({ status: "unavailable" });
          return;
        }
        if (active) setState({ status: "ready", data });
      } catch {
        if (active) setState({ status: "unavailable" });
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  if (state.status === "loading") {
    return (
      <section className="dg-sb" aria-busy="true">
        <div className="dg-sb__skeleton" />
        <div className="dg-sb__skeleton dg-sb__skeleton--short" />
      </section>
    );
  }

  if (state.status === "unavailable") {
    return (
      <section className="dg-sb">
        <h2 className="dg-sb__title">Model record</h2>
        <p className="dg-sb__scope">
          The record is unavailable right now. Nothing has been graded away — the
          validated results and any live weeks are still on disk; this surface just
          cannot read them at the moment.
        </p>
      </section>
    );
  }

  const {
    market_question: market,
    baseline_question: base,
    position_scope,
    live,
  } = state.data;
  const studied = position_scope.studied.join(", ");

  return (
    <section className="dg-sb" aria-labelledby="dg-sb-title">
      <header className="dg-sb__head">
        <h2 className="dg-sb__title" id="dg-sb-title">
          {studied} model record
        </h2>
        <p className="dg-sb__scope">{position_scope.note}</p>
      </header>

      {/* Question 1 — the edge question. Leads, because if the model does not beat the
          market the market is free. Its answer today is "not yet", stated as an answer. */}
      <article className="dg-sb__q dg-sb__q--market">
        <p className="dg-sb__qlabel">Against the market</p>
        <p className="dg-sb__verdict">{market.headline}</p>
        <dl className="dg-sb__facts">
          <div>
            <dt>Why not</dt>
            <dd>{market.why}</dd>
          </div>
          <div>
            <dt>What would answer it</dt>
            <dd>{market.what_would_answer_it}</dd>
          </div>
        </dl>
        <p className="dg-sb__note">{market.effect_direction_note}</p>
        <p className="dg-sb__denominator">
          <span className="dg-sb__num">{market.evaluable_folds}</span> of{" "}
          <span className="dg-sb__num">{market.total_folds}</span> test seasons usable
        </p>
      </article>

      {/* Question 2 — the naive baseline. Answered, and the answer carries its own
          uncertainty at equal weight: direction established, magnitude maybe immaterial. */}
      <article className="dg-sb__q dg-sb__q--model">
        <p className="dg-sb__qlabel">Against last year&rsquo;s points per game</p>
        <p className="dg-sb__verdict">{base.headline}</p>

        <div className="dg-sb__figure">
          <span className="dg-sb__value">{signed(base.effect.value)}</span>
          <span className="dg-sb__unit">
            Spearman rank&#8209;correlation
            <em className="dg-sb__unitwarn">
              a ranking-quality difference, not fantasy points
            </em>
          </span>
        </div>

        <p className="dg-sb__range">
          Plausible range{" "}
          <span className="dg-sb__num">
            {base.effect.ci_low?.toFixed(3)} to {base.effect.ci_high?.toFixed(3)}
          </span>{" "}
          &middot; materiality floor{" "}
          <span className="dg-sb__num">{base.materiality_floor.toFixed(2)}</span>{" "}
          &middot; <span className="dg-sb__num">{base.effect.evaluable_folds}</span> of{" "}
          <span className="dg-sb__num">{base.effect.total_folds}</span> seasons
        </p>

        {base.below_materiality_floor && (
          <p className="dg-sb__counterweight">{base.materiality_note}</p>
        )}

        <p className="dg-sb__counterweight">
          {base.counterweight_headline}{" "}
          <span className="dg-sb__num">{signed(base.counterweight_effect.value)}</span>
        </p>
      </article>

      {/* Live accrual. Denominators inline — a rank statistic over 318 of 501
          predictions is a different claim than one over 501. */}
      <article className="dg-sb__q dg-sb__q--live">
        <p className="dg-sb__qlabel">Live weekly record</p>
        <p className="dg-sb__verdict dg-sb__verdict--quiet">{live.headline}</p>
        {live.state === "accruing" && (
          <p className="dg-sb__denominator">
            <span className="dg-sb__num">{live.predictions_graded}</span> of{" "}
            <span className="dg-sb__num">{live.predictions_declared}</span> predictions
            graded &middot; <span className="dg-sb__num">{live.rank_eligible}</span>{" "}
            rank&#8209;eligible
          </p>
        )}
        <p className="dg-sb__note">{live.rank_availability_note}</p>
      </article>

      <footer className="dg-sb__foot">
        <p className="dg-sb__note">
          {state.data.study_label} &middot; descriptive record only &mdash; it reports
          how the model has scored, never what to do.
        </p>
      </footer>
    </section>
  );
}
