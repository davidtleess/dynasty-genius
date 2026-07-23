"""
Pre-draft QB ranking backtest, 2018-2021 classes (top 5 drafted QBs each).

RULES (locked before scoring):
- Inputs are ONLY things knowable before that year's NFL draft:
  final college season stats, age on draft day, recruiting stars,
  level of competition. NO draft position. NO NFL data.
- Model weights are taken from the hardened spec agreed previously,
  fixed here BEFORE any outcome comparison:
    0.35 * z(rush yds/gm)      (sacks included as NCAA counts them, uniformly)
    0.10 * z(rush TD/gm)
    0.25 * z(AY/A)             adjusted yards per attempt = (yds + 20*TD - 45*INT)/att
    0.10 * z(comp %)
    0.15 * z(-draft age)       younger is better, down-weighted per research
    0.05 * (stars - 3) / 2     weak recruiting prior
- Competition multiplier applied to rush yds/gm, rush TD/gm, AY/A before
  z-scoring (declared up front, not tuned):
    FCS = 0.75, Group of 5 / weak slate = 0.80, BYU 2020 covid slate = 0.85, P5 = 1.0
- z-scores computed WITHIN each class (that's the ranking task).

Outcome label: realized Superflex dynasty value rank within class through the
2025 season (1 = most valuable career-to-date asset). Assigned from public
consensus, documented, disputable.

Baseline to beat: actual NFL draft order of the same 5 QBs.
Metric: Spearman rank correlation vs outcome, per class and pooled.
"""

import statistics as st

# name, games, rush_yds, rush_td, comp_pct, pass_att, pass_yds, pass_td, ints,
# draft_age, stars, comp_mult, actual_draft_order(1=first QB taken), outcome_rank
DATA = {
    2018: [
        ("Baker Mayfield", 14, 311, 5, 70.5, 404, 4627, 43, 6, 23.0, 3, 1.00, 1, 3),
        ("Sam Darnold",    14,  85, 2, 63.1, 480, 4143, 26, 13, 20.9, 4, 1.00, 2, 4),
        ("Josh Allen",     11, 204, 5, 56.3, 270, 1812, 16, 6, 21.9, 2, 0.80, 3, 1),
        ("Josh Rosen",     11, -130, 2, 62.6, 452, 3756, 26, 10, 21.2, 5, 1.00, 4, 5),
        ("Lamar Jackson",  13, 1601, 18, 59.1, 430, 3660, 27, 10, 21.3, 4, 1.00, 5, 2),
    ],
    2019: [
        ("Kyler Murray",    14, 1001, 12, 69.0, 377, 4361, 42, 7, 21.7, 5, 1.00, 1, 1),
        ("Daniel Jones",    11,  319, 3, 60.5, 392, 2674, 22, 9, 21.9, 3, 1.00, 2, 2),
        ("Dwayne Haskins",  14,  108, 4, 70.0, 533, 4831, 50, 8, 21.9, 4, 1.00, 3, 5),
        ("Drew Lock",       13,  175, 2, 62.9, 437, 3498, 28, 8, 22.4, 3, 1.00, 4, 4),
        ("Gardner Minshew", 13,  119, 4, 70.7, 662, 4776, 38, 9, 22.9, 2, 1.00, 5, 3),
    ],
    2020: [
        ("Joe Burrow",     15,  368, 5, 76.3, 527, 5671, 60, 6, 23.4, 4, 1.00, 1, 2),
        ("Tua Tagovailoa",  9,   17, 2, 71.4, 252, 2840, 33, 3, 22.1, 5, 1.00, 2, 5),
        ("Justin Herbert", 14,   50, 4, 66.8, 428, 3471, 32, 6, 22.1, 3, 1.00, 3, 3),
        ("Jordan Love",    13,  175, 1, 61.9, 473, 3402, 20, 17, 21.5, 2, 0.80, 4, 4),
        ("Jalen Hurts",    14, 1298, 20, 69.7, 340, 3851, 32, 8, 21.7, 4, 1.00, 5, 1),
    ],
    2021: [
        ("Trevor Lawrence", 10,  203, 8, 69.2, 334, 3153, 24, 5, 21.5, 5, 1.00, 1, 1),
        ("Zach Wilson",     12,  254, 10, 73.5, 336, 3692, 33, 3, 21.7, 3, 0.85, 2, 4),
        # Lance: 2020 was 1 game, so his last full season (2019 FCS) is used.
        ("Trey Lance",      16, 1100, 14, 66.9, 287, 2786, 28, 0, 20.9, 3, 0.75, 3, 5),
        ("Justin Fields",    8,  383, 5, 70.2, 225, 2100, 22, 6, 22.1, 5, 1.00, 4, 2),
        ("Mac Jones",       13,   14, 1, 77.4, 402, 4500, 41, 4, 22.6, 3, 1.00, 5, 3),
    ],
}

W_RYPG, W_RTD, W_AYA, W_CMP, W_AGE, W_STARS = 0.35, 0.10, 0.25, 0.10, 0.15, 0.05


def z(vals):
    m, s = st.mean(vals), st.pstdev(vals)
    return [(v - m) / s if s else 0.0 for v in vals]


def spearman(a, b):
    ra = {v: i + 1 for i, v in enumerate(sorted(a))}
    rb = {v: i + 1 for i, v in enumerate(sorted(b))}
    d2 = sum((ra[x] - rb[y]) ** 2 for x, y in zip(a, b))
    n = len(a)
    return 1 - 6 * d2 / (n * (n * n - 1))


pooled_model, pooled_draft, pooled_out = [], [], []
print(f"{'':16}{'model':>7}{'draft':>7}{'actual':>8}")
for year, rows in DATA.items():
    rypg = [r[2] / r[1] * r[11] for r in rows]
    rtd = [r[3] / r[1] * r[11] for r in rows]
    aya = [((r[6] + 20 * r[7] - 45 * r[8]) / r[5]) * r[11] for r in rows]
    cmp_ = [r[4] for r in rows]
    age = [-r[9] for r in rows]
    z1, z2, z3, z4, z5 = z(rypg), z(rtd), z(aya), z(cmp_), z(age)
    scores = [
        W_RYPG * z1[i] + W_RTD * z2[i] + W_AYA * z3[i] + W_CMP * z4[i]
        + W_AGE * z5[i] + W_STARS * (rows[i][10] - 3) / 2
        for i in range(len(rows))
    ]
    order = sorted(range(len(rows)), key=lambda i: -scores[i])
    model_rank = [0] * len(rows)
    for pos, i in enumerate(order):
        model_rank[i] = pos + 1

    print(f"\n=== {year} class ===")
    for i, r in enumerate(rows):
        print(f"{r[0]:18} model#{model_rank[i]}  draft#{r[12]}  outcome#{r[13]}  score={scores[i]:+.2f}")

    out = [r[13] for r in rows]
    draft = [r[12] for r in rows]
    sm = spearman(model_rank, out)
    sd = spearman(draft, out)
    print(f"Spearman vs outcome: stats-only model {sm:+.2f} | actual draft order {sd:+.2f}")

    base = max(pooled_out, default=0)
    pooled_model += [m + base for m in model_rank]
    pooled_draft += [d + base for d in draft]
    pooled_out += [o + base for o in out]

print("\n=== Pooled (within-class ranks, 20 QBs) ===")
print(f"stats-only model vs outcomes: {spearman(pooled_model, pooled_out):+.2f}")
print(f"actual draft order vs outcomes: {spearman(pooled_draft, pooled_out):+.2f}")
