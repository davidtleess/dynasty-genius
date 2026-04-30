from app.services.rookie_evaluator import score_prospect

PICK_BASE_VALUES = {1: 80.0, 2: 45.0, 3: 20.0, 4: 10.0}

AGE_DISCOUNT = {
    "RB": {"baseline": 23, "rate": 0.12},
    "WR": {"baseline": 24, "rate": 0.09},
    "TE": {"baseline": 25, "rate": 0.08},
    "QB": {"baseline": 28, "rate": 0.07},
}

VERDICT_THRESHOLDS = [
    (20.0,  "Strong win"),
    (8.0,   "Win"),
    (-8.0,  "Fair"),
    (-20.0, "Loss"),
]


def value_pick(round_num: int, year: int, current_year: int = 2025) -> float:
    base = PICK_BASE_VALUES.get(round_num, 5.0)
    years_away = year - current_year
    if years_away <= 0:
        return base
    return round(base * (0.85 ** years_away), 1)


def value_player(position: str, age: int, pick: int, round_num: int) -> float:
    result = score_prospect(position=position, pick=pick, round_num=round_num, age=float(age))
    ppg = result["predicted_y24_ppg"]
    base = ppg * 6.0

    discount = AGE_DISCOUNT.get(position)
    if discount is None:
        return round(base, 1)

    age_multiplier = max(0.0, 1.0 - (max(0, age - discount["baseline"]) * discount["rate"]))
    return round(base * age_multiplier, 1)


def _score_asset(asset: dict) -> dict:
    if asset["type"] == "pick":
        value = value_pick(round_num=asset["round"], year=asset["year"])
        return {**asset, "value": value}
    elif asset["type"] == "player":
        value = value_player(
            position=asset["position"],
            age=asset["age"],
            pick=asset["pick"],
            round_num=asset["round"],
        )
        return {**asset, "value": value}
    else:
        raise ValueError(f"Unknown asset type: {asset['type']}")


def analyze_trade(my_assets: list[dict], their_assets: list[dict]) -> dict:
    my_scored = [_score_asset(a) for a in my_assets]
    their_scored = [_score_asset(a) for a in their_assets]

    my_total = round(sum(a["value"] for a in my_scored), 1)
    their_total = round(sum(a["value"] for a in their_scored), 1)
    difference = round(my_total - their_total, 1)

    verdict = "Strong loss"
    for threshold, label in VERDICT_THRESHOLDS:
        if difference >= threshold:
            verdict = label
            break

    return {
        "my_total":          my_total,
        "their_total":       their_total,
        "difference":        difference,
        "verdict":           verdict,
        "my_assets_scored":  my_scored,
        "their_assets_scored": their_scored,
    }
