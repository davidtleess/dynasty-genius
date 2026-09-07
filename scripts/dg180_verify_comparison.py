"""Independent acceptance oracle: compare the API with frozen original producer data."""
import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path
from urllib.request import urlopen

BASE = Path(__file__).resolve().parents[1] / 'runs'
REPORT = BASE / '20260906T214512Z/dg178_audit/report.json'
CATALOG = BASE / '20260907T013635Z/dg178_available_catalog/catalog.json'
REPORT_SHA = '19e032a4067dff1759199a84720c0f879bb61f792fd3b2703808b55485a7af37'
CATALOG_SHA = 'd08e89087c5038439d81421cfacba186ebedd4619be9d0015a9c42b74938597e'
YEARS = list(range(2026, 2031))


def bound_json(path, expected):
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == expected, path
    return json.loads(raw)


def close(actual, expected, context):
    if expected is None:
        assert actual is None, (context, actual, expected)
    else:
        assert isinstance(actual, (int, float)) and not isinstance(actual, bool), context
        assert math.isfinite(actual), context
        # The API reconstructs roster values by adding the stored signed margin
        # and reference. Allow floating-point addition noise, never display rounding.
        assert math.isclose(actual, expected, abs_tol=1e-10, rel_tol=1e-12), (context, actual, expected)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runs-root', type=Path, default=BASE)
    parser.add_argument('--url')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    report = bound_json(args.runs_root / REPORT.relative_to(BASE), REPORT_SHA)
    catalog = bound_json(args.runs_root / CATALOG.relative_to(BASE), CATALOG_SHA)
    snapshot = bound_json(Path(report['inputs']['snapshot']['path']), report['inputs']['snapshot']['sha256'])
    david = next(r for r in snapshot['rosters'] if r['roster_id'] == snapshot['david_roster_id'])
    stored = set(david['taxi'] or []) | set(david['reserve'] or [])
    catalog_by_id = {r['sleeper_id']: r for r in catalog['rows_detail']}
    producers = {}
    for key, source in catalog['sources']['producers'].items():
        raw = Path(source['csv']).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == source['sha256']
        rows = list(csv.DictReader(io.StringIO(raw.decode())))
        lookup = {r.get('player_id') or r['gsis_id']: r for r in rows}
        assert len(rows) == len(lookup)
        producers[key] = lookup
    expected = {'roster': {}, 'available': {}}
    bridge_bytes = Path(report['identity_bridge']['path']).read_bytes()
    assert hashlib.sha256(bridge_bytes).hexdigest() == report['identity_bridge']['sha256']
    bridges = {}
    for entry in csv.DictReader(io.StringIO(bridge_bytes.decode())):
        if entry['gsis_id']:
            bridges.setdefault(entry['sleeper_id'], set()).add(entry['gsis_id'])
    board = report['horizon_board']
    for row in board['davids_roster']:
        gsis = row['player_id']
        if gsis not in producers[row['producer']]:
            candidates = bridges[row['sleeper_id']]
            assert len(candidates) == 1, row['name']
            gsis = next(iter(candidates))
        source = producers[row['producer']][gsis]
        points = [float(source[f'e_points_year{h}']) for h in range(1, 6)]
        assert all(math.isfinite(p) for p in points)
        expected['roster'][row['sleeper_id']] = {
            'name': row['name'], 'position': row['position'],
            'team': catalog_by_id[row['sleeper_id']]['nfl_team'],
            'status': catalog_by_id[row['sleeper_id']]['availability_class'],
            'taxi_or_reserve': row['sleeper_id'] in stored,
            'points': points, 'now_points': points[0], 'future_points': sum(points[1:]),
        }
    assert len(expected['roster']) == len(board['davids_roster']) == 27
    assert set(expected['roster']) == set(david['players'])
    assert len(stored) == 6
    for row in catalog['rows_detail']:
        if row['population'] == 'owned':
            continue
        by_year = {s['season']: s['e_points'] for s in (row.get('forecast') or {}).get('seasons', [])}
        points = [by_year.get(y) for y in YEARS]
        expected['available'][row['sleeper_id']] = {
            'name': row['name'], 'position': row['league_position'],
            'team': row['nfl_team'], 'status': row['availability_class'],
            'population': row['population'], 'starting_estimate': row['starting_estimate'],
            'points': points, 'now_points': row['now_points'], 'future_points': row['future_points'],
        }
    pool = [r for r in expected['available'].values() if r['population'] == 'default']
    assert len(pool) == 433
    assert sum(r['now_points'] is not None for r in pool) == 360
    assert sum(r['starting_estimate'] for r in pool) == 7
    assert not (expected['roster'].keys() & expected['available'].keys())
    checked = 0
    if args.url:
        with urlopen(args.url, timeout=30) as response:
            assert response.status == 200
            payload = json.load(response)
        (args.out / 'comparison.json').write_text(json.dumps(payload, indent=2))
        assert payload['source']['report_sha256'] == REPORT_SHA
        assert payload['source']['report_run'] == '20260906T214512Z'
        assert payload['source']['catalog_run'] == '20260907T013635Z'
        assert payload['forecast_years'] == YEARS
        assert payload['future_years'] == YEARS[1:]
        for population in expected:
            got = {r['sleeper_id']: r for r in payload[population]}
            assert len(got) == len(payload[population])
            assert got.keys() == expected[population].keys(), population
            for sid, reference in expected[population].items():
                row = got[sid]
                assert (row['name'], row['position']) == (reference['name'], reference['position'])
                assert (row['team'], row['status']) == (reference['team'], reference['status'])
                assert [s['season'] for s in row['seasons']] == YEARS
                for key in ('now_points', 'future_points'):
                    close(row[key], reference[key], (population, sid, key))
                    checked += 1
                for season, value in zip(row['seasons'], reference['points'], strict=True):
                    close(season['points'], value, (population, sid, season['season']))
                    checked += 1
                if population == 'available':
                    assert row['starting_estimate'] == reference['starting_estimate']
                    assert row['population'] == reference['population']
                else:
                    assert row['taxi_or_reserve'] == reference['taxi_or_reserve']
                assert row['evidence_note'] and isinstance(row['evidence_note'], str)
    result = {'report_sha256': REPORT_SHA, 'catalog_sha256': CATALOG_SHA,
              'roster': len(expected['roster']), 'available': len(expected['available']),
              'default_pool': len(pool), 'numbered': 360, 'starting': 7, 'missing': 73,
              'numeric_fields_verified': checked, 'api_checked': bool(args.url)}
    (args.out / 'expected.json').write_text(json.dumps(expected, indent=2))
    (args.out / 'result.json').write_text(json.dumps(result, indent=2))
    print(json.dumps({'evidence': str(args.out), **result}))


if __name__ == '__main__':
    main()
