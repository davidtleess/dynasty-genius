# SUPERSEDED — quote the successor, not this run

Defect found by lane 25057 (DG-178) on 2026-09-06 while grading the assembled board: in this run
`evaluation.json` and `out_of_time_predictions.csv` describe the PLAIN arm (written before the
trend experiment decided), while `rookie_scores_2026.csv` was scored by the auto-selected
TREND model. A consumer graded the plain arm's predictions against a trend-scored class file.
The successor writes the scoring arm's evaluation and predictions as the canonical files and
the other arm beside them (`evaluation_other_arm_*.json`, `out_of_time_predictions_*.csv`).
The scored class, the trend decision and every other number here are reproduced by the successor.

Kept intact as evidence; every file is as the run wrote it.
