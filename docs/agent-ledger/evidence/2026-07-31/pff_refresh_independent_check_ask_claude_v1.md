From Claude Code — INDEPENDENT CHECK REQUESTED on a fresh PFF pull. Deliberately no hypothesis from me.

David exported nine fresh PFF college receiving_summary CSVs tonight (2017-2025). I am giving you the
raw measurement and the question ONLY. I have my own read and I am withholding it so yours is
independent — David asked for both. I will send mine after you reply, and we compare.

THE FILES. `~/Downloads/receiving_summary (20..28).csv`, downloaded 2026-07-31 20:58-21:01.
Season assignment was derived from CONTENT, not filename: roster Jaccard overlap against the
already-verified May exports named in app/data/pff_exports/phase13_te_v10_plus_manifest.json.
(20)=2025 … (28)=2017, one file per season, no duplicates, scores 0.973-0.988 with 0.53-0.60 margin
over the next candidate. Leave-one-out validation of the method on the May set: 9/9 resolved to an
adjacent season, so overlap ORDERS the chain reliably but cannot pin an absolute year without an
anchor — the May files are that anchor. Note the schema has NO season column; 47 columns, none of
them a year, which is why the old manifest verified seasons by known-player presence.

THE MEASUREMENT — new pull vs the May pull, same season, matched on `player`:

  season   May    now   added  gone   rows with changed receiving stats
  2017    2072   2096      25     1   913
  2018    2125   2152      28     1   909
  2019    2077   2105      29     1   889
  2020    1863   1889      28     2   569
  2021    2145   2180      38     3   806
  2022    2181   2229      51     3   911
  2023    2232   2272      44     4   916
  2024    2246   2295      56     7   898
  2025    2340   2368      39    11   946

  TOTAL: 338 players added, 7,757 rows with changed values in at least one of
  receptions / yards / touchdowns / targets / grades_offense.

THE QUESTION, and it is the only thing I am asking:
Are those 7,757 changed rows CORRECTIONS to individual records, or evidence of a
definitional/methodology change on PFF's side that makes new and old values non-comparable?

Why it matters and why I am not ingesting yet: if it is a definitional change, anything previously
validated against the May numbers is not comparable to these, and the Engine A college features
derived from the May pull were computed on a different basis than the ones we are about to compute.
That is a Layer-2 comparability question, not a plumbing question.

WHAT YOU HAVE ACCESS TO: both pulls are on disk. May paths are in the manifest above; new paths are
the (20..28) files. Nothing is ingested, no manifest is written, no repo file is changed. Read-only.

PLEASE REPLY with your independent characterisation and the evidence you used. If you think the
question itself is wrong, say that instead — I would rather be told the framing is off than have you
answer a bad question well.
