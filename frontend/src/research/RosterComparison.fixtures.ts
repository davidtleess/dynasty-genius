// DG-181 test fixture — a comparison payload shaped exactly like the DG-182 contract, with real
// identities and magnitudes from catalog 20260907T013635Z and report 20260906T214512Z (roster
// expected points are full-precision reconstructions, margin + position reference, so the
// difference tests are exact). Two synthetic rows exist only to exercise edges the real data does
// not: an exact tie / under-one-point pair, and a zero-versus-missing row. Tests only; never
// imported by product code.
import type { ComparisonPayload, ComparisonPlayer } from "./comparisonHelpers";

const YEARS = [2026, 2027, 2028, 2029, 2030];

function seasons(points: (number | null)[], classes?: (string | null)[]) {
  return YEARS.map((season, i) => ({
    season,
    points: points[i] ?? null,
    estimate_class: classes?.[i] ?? null,
  }));
}

const STARTING_CLASSES = [
  "cold_start_candidate",
  "baseline_research_candidate",
  "baseline_research_candidate",
  "baseline_research_candidate",
  "baseline_research_candidate",
];

export const flacco: ComparisonPlayer = {
  sleeper_id: "19",
  name: "Joe Flacco",
  position: "QB",
  team: "CIN",
  population: "default",
  status: "active",
  now_points: 115.32497628242587,
  future_points: 179.44179369437418,
  seasons: seasons([
    115.32497628242587, 85.90292286152696, 44.487410939143025, 31.467770472882492,
    17.583689420821695,
  ]),
  starting_estimate: false,
  missing_reason: null,
  evidence_note:
    "Accepted DG-177 veteran annual forecast; every year is the producer's own expected season points.",
};

export const rourke: ComparisonPlayer = {
  sleeper_id: "12477",
  name: "Kurtis Rourke",
  position: "QB",
  team: "SF",
  population: "default",
  status: "active",
  now_points: -0.2117124292497116,
  future_points: 38.578925122738816,
  seasons: seasons(
    [
      -0.2117124292497116, 10.991481481481483, 11.166796116504855, 9.695247524752476,
      6.7254,
    ],
    STARTING_CLASSES,
  ),
  starting_estimate: true,
  missing_reason: null,
  evidence_note:
    "Starting estimate: 2026 from the draft-capital candidate, 2027–2030 from the position's historical baseline; not an accepted forecast.",
};

export const mertz: ComparisonPlayer = {
  ...rourke,
  sleeper_id: "12705",
  name: "Graham Mertz",
  team: "HOU",
  status: "injured_reserve",
  now_points: 0.5578664679454675,
  seasons: seasons(
    [
      0.5578664679454675, 10.991481481481483, 11.166796116504855, 9.695247524752476,
      6.7254,
    ],
    STARTING_CLASSES,
  ),
};

export const prentice: ComparisonPlayer = {
  sleeper_id: "8025",
  name: "Adam Prentice",
  position: "RB",
  team: "DEN",
  population: "default",
  status: "practice_squad",
  now_points: 10.197681979436744,
  future_points: 8.545248489434728,
  seasons: seasons([
    10.197681979436744, 3.770280866250476, 2.522325552928488, 1.1616111469658732,
    1.0910309232898907,
  ]),
  starting_estimate: false,
  missing_reason: null,
  evidence_note:
    "Recovered from the producer's frozen file under the census's verified NFL identity; not among the accepted board rows.",
};

export const bradley: ComparisonPlayer = {
  sleeper_id: "11851",
  name: "Carter Bradley",
  position: "QB",
  team: "JAX",
  population: "default",
  status: "injured_reserve",
  now_points: null,
  future_points: null,
  seasons: seasons([null, null, null, null, null]),
  starting_estimate: false,
  missing_reason: "no forecast from the selected producers; no reason stated",
  evidence_note: "No forecast on file.",
};

export const armstrong: ComparisonPlayer = {
  sleeper_id: "12863",
  name: "Andrew Armstrong",
  position: "WR",
  team: "KC",
  population: "default",
  status: "practice_squad",
  now_points: null,
  future_points: null,
  seasons: seasons([null, null, null, null, null]),
  starting_estimate: false,
  missing_reason: "no forecast from the selected producers; no reason stated",
  evidence_note: "No forecast on file.",
};

export const martinez: ComparisonPlayer = {
  sleeper_id: "11065",
  name: "Adrian Martinez",
  position: "QB",
  team: "SF",
  population: "cut",
  status: "cut",
  now_points: 3.4162459189407786,
  future_points: 20.206926277737594,
  seasons: seasons([
    3.4162459189407786, 1.7798945893140405, 5.8041545795711045, 5.65630358247742,
    6.966573526375029,
  ]),
  starting_estimate: false,
  missing_reason: null,
  evidence_note:
    "Accepted DG-177 veteran annual forecast; the dated census lists him cut.",
};

// Synthetic: a 2026 forecast of exactly zero points with no later years.
export const zeroCase: ComparisonPlayer = {
  sleeper_id: "z0",
  name: "Zero Case",
  position: "WR",
  team: null,
  population: "default",
  status: "active",
  now_points: 0,
  future_points: null,
  seasons: seasons([0, null, null, null, null]),
  starting_estimate: false,
  missing_reason: null,
  evidence_note: "2026 forecast is exactly zero points; later years absent.",
};

export const mccarthy: ComparisonPlayer = {
  sleeper_id: "11565",
  name: "J.J. McCarthy",
  position: "QB",
  team: "MIN",
  population: "owned",
  status: "rostered",
  now_points: 156.5816995883777,
  future_points: 832.2660448226352,
  seasons: seasons([
    156.5816995883777, 172.7485573843338, 208.52145323820008, 220.31020979991473,
    230.68621745986795,
  ]),
  starting_estimate: false,
  missing_reason: null,
  evidence_note:
    "Accepted DG-177 veteran annual forecast from the five-year research report; expected season points, not the impact number.",
};

export const ali: ComparisonPlayer = {
  ...mccarthy,
  sleeper_id: "11570",
  name: "Rasheen Ali",
  position: "RB",
  team: "BAL",
  now_points: 52.07419940832724,
  future_points: 410.4238857735934,
  seasons: seasons([
    52.07419940832724, 93.09579923378813, 106.0509484321951, 113.16719756484613,
    98.11994054276404,
  ]),
};

export const macJones: ComparisonPlayer = {
  ...mccarthy,
  sleeper_id: "7527",
  name: "Mac Jones",
  team: "SF",
  now_points: 160.87349867860095,
  future_points: 771.9,
  seasons: seasons([
    160.87349867860095, 177.51440362037368, 209.58353047413885, 190.1, 194.7,
  ]),
};

export const dell: ComparisonPlayer = {
  ...mccarthy,
  sleeper_id: "9502",
  name: "Tank Dell",
  position: "WR",
  team: "HOU",
  now_points: null,
  future_points: null,
  seasons: seasons([null, null, null, null, null]),
  missing_reason: "0 games in 2025, so this producer has no feature row for him",
  evidence_note: "No accepted forecast row; identity not covered by the producer.",
  taxi_or_reserve: true,
};

// Synthetic: equal to Flacco for 2026 and 0.03 points above him for 2027–2030.
export const tieTwin: ComparisonPlayer = {
  ...mccarthy,
  sleeper_id: "tt",
  name: "Tie Twin",
  team: "MIN",
  now_points: 115.32497628242587,
  future_points: 179.47179369437418,
  seasons: seasons([115.32497628242587, 85.9, 44.5, 31.5, 17.57179369437418]),
  evidence_note: "Synthetic fixture row for the tie and under-one-point paths.",
};

export const comparisonPayload: ComparisonPayload = {
  source: {
    report_run: "20260906T214512Z",
    catalog_run: "20260907T013635Z",
    report_sha256: "19e032a4067dff1759199a84720c0f879bb61f792fd3b2703808b55485a7af37",
    ownership_as_of: "2026-09-06T13:00:52.63597+00:00",
    nfl_status_as_of: "Sun, 06 Sep 2026 11:28:11 GMT",
  },
  forecast_years: YEARS,
  future_years: [2027, 2028, 2029, 2030],
  scoring_note:
    "Research PPR over the championship window (weeks 1–17); not your league's exact scoring.",
  available: [flacco, rourke, mertz, prentice, bradley, armstrong, martinez, zeroCase],
  roster: [mccarthy, ali, macJones, dell, tieTwin],
};
