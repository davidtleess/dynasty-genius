"""Project verified immutable records into a manager-facing, source-pinned view."""
import math
import re
from copy import deepcopy
from datetime import datetime

SOURCE_KEYS = ('report_run', 'report_sha256', 'market_sha256', 'league_sha256', 'catalog_run', 'catalog_content_sha256')
RECEIPT_KEYS = ('snapshot_id', 'saved_at', 'forecast_date', 'market_as_of', 'ownership_as_of', 'report_generated_at', 'catalog_generated_at', 'years', 'counts', 'source', 'evaluation_status', 'evaluation_plan')
STATES = {'not_registered', 'awaiting_horizon', 'awaiting_capture', 'input_unavailable', 'cutoff_ineligible', 'insufficient_evidence', 'graded'}


def safe_receipt(receipt):
    result = {key: deepcopy(receipt.get(key)) for key in RECEIPT_KEYS}
    result['source'] = {key: receipt['source'][key] for key in SOURCE_KEYS}
    return result


def _stamp(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('Record time must include a timezone')
    return parsed


def _finite_document(value):
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError('Nonfinite evaluation number')
    if isinstance(value, dict):
        for child in value.values():
            _finite_document(child)
    if isinstance(value, list):
        for child in value:
            _finite_document(child)


def _validate_result(result):
    if not isinstance(result, dict) or not isinstance(result.get('summary'), str):
        raise ValueError('Result summary missing')
    for key in ('comparisons', 'rows', 'details'):
        if not isinstance(result.get(key), list):
            raise ValueError('Result content missing')
    for comparison in result['comparisons']:
        for name in ('id', 'label', 'units', 'state', 'note'):
            if not isinstance(comparison.get(name), str):
                raise ValueError('Comparison label missing')
        value = comparison.get('estimate')
        if value is not None and type(value) not in (int, float):
            raise ValueError('Invalid comparison estimate')
        interval = comparison.get('interval95')
        if interval is not None and (not isinstance(interval, list) or len(interval) != 2 or any(type(n) not in (int, float) for n in interval) or interval[0] > interval[1]):
            raise ValueError('Invalid comparison interval')
        if any(type(comparison.get(n)) is not int or comparison[n] < 0 for n in ('eligible', 'scored')) or comparison['scored'] > comparison['eligible']:
            raise ValueError('Invalid comparison counts')
    _finite_document(result)


def _pending(claim, selected):
    production = claim == 'football_production'
    return {
        'state': 'input_unavailable' if production and selected else 'not_registered',
        'reason': ('The forecast is saved. Its comparison baselines have not been saved for evaluation yet.' if production and selected else 'No market-movement study is enrolled for this reading.' if selected else 'Choose a saved reading to see what can be evaluated.'),
        'window': {'label': '2026 regular-season weeks 1–17' if production else '90 days after enrollment · 30-day descriptive check', 'start_at': None, 'end_at': None},
        'provenance_class': 'unavailable',
        'counts': {'eligible': 0, 'scored': 0, 'missing': 0},
        'observations': [], 'result': None,
    }


def _observations(stream, production):
    rows = []
    for row in stream.get('rows', []):
        gap = None
        if not production and row.get('our_rank') and row.get('market_rank'):
            gap = sum(row['market_rank']) / 2 - sum(row['our_rank']) / 2
        rows.append({
            'sleeper_id': row['sleeper_id'], 'name': row['name'], 'position': row['position'],
            'producer': row.get('producer'), 'provenance': row.get('provenance', 'original'),
            'forecast': row.get('forecast') if production else gap,
            'baseline': (row.get('baselines') or {}).get('prior_season') if production else row.get('momentum'),
            'baseline_position_median': (row.get('baselines') or {}).get('position_median') if production else None,
            'outcome': None, 'error': None,
            'reason': '; '.join(str(reason) for reason in row.get('missing_reasons', {}).values()) or None,
        })
    return rows


def _stream(claim, selected, enrollments, grades):
    if not selected:
        return _pending(claim, selected)
    key = 'production' if claim == 'football_production' else 'market'
    candidates = [record for record in enrollments if record['document']['snapshot_id'] == selected['snapshot_id']]
    if not candidates:
        if any(record['document'].get('snapshot_id') == selected['snapshot_id'] for record in grades):
            raise ValueError('Grade references a missing enrollment')
        return _pending(claim, selected)
    candidates.sort(key=lambda r: (_stamp(r['document']['enrolled_at']), r['record_id']))
    usable = [r for r in candidates if r['document'][key]['state'] not in {'not_registered', 'input_unavailable', 'cutoff_ineligible'}]
    enrollment = (usable or candidates)[0]
    document = enrollment['document']
    if document['source'] != selected['source']:
        raise ValueError('Enrollment source differs from saved reading')
    stream = document[key]
    if stream['state'] not in STATES:
        raise ValueError('Invalid enrollment state')
    result = {field: deepcopy(stream[field]) for field in ('state', 'reason', 'window', 'provenance_class')}
    result['observations'] = _observations(stream, key == 'production')
    result['counts'] = {'eligible': len(stream.get('rows', [])), 'scored': 0, 'missing': sum(row['forecast'] is None or row['baseline'] is None or (key == 'production' and row['baseline_position_median'] is None) for row in result['observations'])}
    result['result'] = None
    possible = []
    for record in grades:
        grade = record['document']
        if grade.get('snapshot_id') != selected['snapshot_id']:
            continue
        if grade.get('enrollment_id') not in {r['record_id'] for r in candidates}:
            raise ValueError('Grade references a missing enrollment')
        if grade.get('enrollment_id') != enrollment['record_id'] or grade.get('claim') != claim:
            continue
        if grade.get('schema_version') != 'track_record.grade.v1' or grade.get('decision_supported') is not False:
            raise ValueError('Invalid grade declaration')
        if grade.get('policy_sha256') != stream['plan_sha256']:
            raise ValueError('Grade policy differs from enrollment')
        if not isinstance(grade.get('input_hashes'), dict) or not grade['input_hashes']:
            raise ValueError('Grade input binding missing')
        for name, sha in document['input_hashes'].items():
            if grade['input_hashes'].get(name) != sha:
                raise ValueError('Grade input differs from enrollment')
        if grade.get('state') not in STATES:
            raise ValueError('Invalid grade state')
        horizon = grade.get('horizon_days')
        if (claim == 'market_movement' and (type(horizon) is not int or horizon not in (30, 90))) or (claim == 'football_production' and horizon is not None):
            raise ValueError('Grade horizon missing or invalid')
        if grade['state'] == 'graded' or grade.get('result') is not None:
            _validate_result(grade.get('result'))
            outcomes = grade.get('outcome_source_hashes')
            if not isinstance(outcomes, dict) or not outcomes:
                raise ValueError('Grade outcome binding missing')
            for name, sha in outcomes.items():
                if not isinstance(sha, str) or not re.fullmatch(r'[a-f0-9]{64}', sha) or grade['input_hashes'].get(name) != sha:
                    raise ValueError('Grade outcome hash differs')
        for n in ('eligible', 'scored', 'missing'):
            if type(grade['counts'].get(n)) is not int or grade['counts'][n] < 0:
                raise ValueError('Invalid grade counts')
        if grade['counts']['scored'] > grade['counts']['eligible'] or grade['counts']['missing'] > grade['counts']['eligible']:
            raise ValueError('Scored counts exceed eligibility')
        _finite_document(grade)
        possible.append(grade)
    # Pending checks cannot replace mature evidence. Market horizons remain separate.
    terminal = [g for g in possible if g['state'] in {'graded', 'insufficient_evidence'} and g.get('result') is not None]
    choices = terminal or possible
    if claim == 'market_movement' and choices:
        primary = [g for g in choices if g['horizon_days'] == 90]
        choices = primary or choices
    choices.sort(key=lambda g: _stamp(g['evaluated_at']))
    identities = {}
    for grade in choices:
        identity = (grade['policy_sha256'], tuple(sorted(grade['input_hashes'].items())), grade.get('horizon_days'), grade['state'])
        previous = identities.get(identity)
        content = {k: grade[k] for k in ('counts', 'result')}
        if previous is not None and previous != content:
            raise ValueError('Conflicting grades for identical inputs')
        identities[identity] = content
    if choices:
        grade = choices[0]
        result.update({field: deepcopy(grade[field]) for field in ('state', 'reason', 'window', 'provenance_class', 'counts', 'result')})
        if claim == 'market_movement' and grade['horizon_days'] == 30 and result['result']:
            result['result']['details'] = result['result'].get('details', []) + [{'label': 'Descriptive check', 'value': 'This is the 30-day check. The primary 90-day result is not yet available.'}]
        if len(identities) > 1 and result['result']:
            result['result']['details'] = result['result'].get('details', []) + [{'label': 'Source revisions', 'value': 'Additional outcome revisions are preserved. This view retains the first evaluated reading for this horizon.'}]
    return result


def build_track_record_view(*, snapshots, enrollments, grades, selected_snapshot_id):
    receipts = sorted((safe_receipt(s) for s in snapshots), key=lambda s: (_stamp(s['saved_at']), s['snapshot_id']), reverse=True)
    if selected_snapshot_id:
        selected = next((s for s in receipts if s['snapshot_id'] == selected_snapshot_id), None)
        if selected is None:
            raise FileNotFoundError('Saved reading not found')
    else:
        selected = receipts[0] if receipts else None
    return {
        'schema_version': 'track_record.view.v1', 'status': 'available', 'reason': None,
        'snapshots': receipts, 'selected': selected,
        'production': _stream('football_production', selected, enrollments, grades),
        'market': _stream('market_movement', selected, enrollments, grades),
        'save_capability': {'enabled': False, 'reason': 'Current board sources are not available.', 'expected': None},
    }
