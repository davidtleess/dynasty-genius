# 2027 Class Tracker

Strategic planning reference for future-value decisions involving 2027 rookie picks.

## Generational Anchors

| Prospect | Position | Generational floor |
| --- | --- | ---: |
| Jeremiah Smith | WR | 120 DVU |
| Arch Manning | QB | 120 DVU |

## Trade Rule

Any trade involving 2027 1st-round picks must be evaluated against the 120 DVU generational-anchor premium before acceptance, counter, or rejection language is allowed.

## Delta Gold Anchor Lock

`gen_alpha.gold.anchors` must contain immutable rows for both prospects with `source_rank = 1`, `compliance_tag = STRATEGIC_ANCHOR_LOCK`, and the SHA-256 lock hashes defined in `app/utils/lakehouse_governance.py`.

This tracker is a planning anchor, not a market input. It does not enter Engine A or Engine B scoring.
