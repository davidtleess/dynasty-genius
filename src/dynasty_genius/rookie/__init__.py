"""DG-165 — the draft-capital rookie candidate.

A rookie has no NFL season, so the DG-164 retention cells (keyed on production relative to
the replacement bar) cannot price him. This package estimates, from NFL draft capital alone
(David's 2026-09-06 ruling: "absolutely yes re the draft position"), three explicitly named
quantities per fixed horizon h = 1..5 NFL seasons:

    P(played_h)   at least one regular-season game in seasons 1..h
    P(Q_h)        at least one QUALIFYING season in 1..h  (finished at or above the
                  replacement bar by regular-season PPR total, same bar and tie rule as
                  the canonical DG-164 cells)
    E[N_h]        expected number of qualifying seasons in 1..h — a SEASONS quantity, the
                  unit of the dynasty horizon term, so a rookie needs no retention cell

Nothing here multiplies these together, and nothing here reads a market, projection,
consensus or college column. Composition is the integration lane's decision (DG-178).

Every label is built with an explicit information cutoff: at forecast year T only seasons
<= T - 1 exist, so a class c contributes at horizon h only when c + h - 1 <= T - 1. The
preserved study trained on labels observed through 2025 while "forecasting" 2019; this
package refuses that by construction (see ``labels.horizon_labels`` and
``evaluate.walk_forward_splits``).
"""
