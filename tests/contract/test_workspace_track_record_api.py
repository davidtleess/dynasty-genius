"""Track record preserves saved sources and keeps capture success truthful."""
from copy import deepcopy
from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes import workspace_snapshots as archive
from app.api.routes import workspace_track_record as route
from src.dynasty_genius.adapters.track_record_view import build_track_record_view
from tests.contract.workspace_snapshot_fixtures import write_sources


@pytest.fixture
def setup(tmp_path, monkeypatch):
    paths = write_sources(tmp_path / 'inputs')
    monkeypatch.setenv('DG_WORKSPACE_ARCHIVE_ROOT', str(tmp_path / 'archive'))
    monkeypatch.delenv('DG_EVALUATION_ROOT', raising=False)
    monkeypatch.delenv('DG_TRACK_RECORD_INPUTS_CONFIG', raising=False)
    monkeypatch.setattr(archive, '_current_paths', lambda: paths)
    monkeypatch.setattr(archive, '_now', lambda: datetime(2026, 9, 9, tzinfo=timezone.utc))
    monkeypatch.setattr(archive, '_code_sha', lambda: 'unknown')
    app = FastAPI()
    app.include_router(route.router, prefix='/api')
    client = TestClient(app)
    expected = archive._source(archive.load_workspace_snapshot(*paths))
    return client, tmp_path, expected


def test_empty_get_does_not_create_any_store(setup):
    client, root, expected = setup
    response = client.get('/api/research/track-record')
    assert response.status_code == 200
    body = response.json()
    assert body['status'] == 'available' and body['snapshots'] == []
    assert body['selected'] is None
    assert body['save_capability']['expected'] == expected
    assert not (root / 'archive').exists()


def test_missing_archive_configuration_is_explicit(setup, monkeypatch):
    client, _, _ = setup
    monkeypatch.delenv('DG_WORKSPACE_ARCHIVE_ROOT')
    body = client.get('/api/research/track-record').json()
    assert body['status'] == 'not_configured'
    assert body['save_capability']['enabled'] is False


def test_save_missing_baseline_config_is_partial_success_and_duplicate_stable(setup):
    client, root, expected = setup
    first = client.post('/api/research/track-record/capture', json={'expected': expected})
    assert first.status_code == 200, first.text
    body = first.json()
    assert body['snapshot_status'] == 'saved'
    assert body['enrollment_status'] == 'input_unavailable'
    assert 'saved' in body['reason'].lower()
    second = client.post('/api/research/track-record/capture', json={'expected': expected}).json()
    assert second['snapshot_status'] == 'already_saved'
    assert second['snapshot'] == body['snapshot']
    saved = body['snapshot']
    view = client.get('/api/research/track-record', params={'snapshot_id': saved['snapshot_id']}).json()
    assert view['selected'] == saved
    assert view['production']['state'] == 'input_unavailable'
    assert view['market']['state'] == 'not_registered'
    assert view['selected']['evaluation_status'] == 'ungraded'
    assert str(root) not in str(view)


@pytest.mark.parametrize('field', archive.SOURCE_KEYS)
def test_stale_browser_source_refuses_without_write(setup, field):
    client, root, expected = setup
    expected[field] = 'changed'
    response = client.post('/api/research/track-record/capture', json={'expected': expected})
    assert response.status_code == 409
    assert not (root / 'archive').exists()


def test_unknown_selected_id_does_not_substitute_newest(setup):
    client, _, expected = setup
    client.post('/api/research/track-record/capture', json={'expected': expected})
    assert client.get('/api/research/track-record', params={'snapshot_id': '0' * 64}).status_code == 404
    assert client.get('/api/research/track-record', params={'snapshot_id': '../secret'}).status_code == 422


def test_corrupt_archive_is_unavailable_not_empty(setup):
    client, root, expected = setup
    saved = client.post('/api/research/track-record/capture', json={'expected': expected}).json()['snapshot']
    file = root / 'archive' / saved['snapshot_id'] / 'report.json'
    file.write_bytes(file.read_bytes() + b' ')
    response = client.get('/api/research/track-record')
    assert response.status_code == 503
    assert str(root) not in response.text


def _saved(setup):
    client, _, expected = setup
    return client.post('/api/research/track-record/capture', json={'expected': expected}).json()['snapshot']


def test_no_grade_never_modifies_legacy_receipt(setup):
    saved = _saved(setup)
    before = deepcopy(saved)
    view = build_track_record_view(snapshots=[saved], enrollments=[], grades=[], selected_snapshot_id=saved['snapshot_id'])
    assert view['production']['result'] is None
    assert view['market']['result'] is None
    assert saved == before


def test_mismatched_grade_reference_refuses(setup):
    saved = _saved(setup)
    with pytest.raises(ValueError, match='enrollment'):
        build_track_record_view(snapshots=[saved], enrollments=[], grades=[{'record_id': 'b'*64, 'document': {'snapshot_id': saved['snapshot_id'], 'enrollment_id': 'a'*64}}], selected_snapshot_id=saved['snapshot_id'])


def test_capture_failure_after_archive_save_is_not_reported_as_total_failure(setup, monkeypatch):
    client, _, expected = setup
    def fail(_snapshot_id):
        raise ValueError('private path /private/example')
    monkeypatch.setattr(route, '_enroll_saved', fail)
    response = client.post('/api/research/track-record/capture', json={'expected': expected})
    assert response.status_code == 200
    body = response.json()
    assert body['snapshot_status'] == 'saved'
    assert body['enrollment_status'] == 'input_unavailable'
    assert '/private/example' not in response.text
    assert len(client.get('/api/research/track-record').json()['snapshots']) == 1


def _enrollment(saved):
    stream = {'state': 'awaiting_horizon', 'reason': 'Waiting.', 'plan_sha256': 'c'*64,
              'window': {'label': '90 days', 'start_at': '2026-09-09T00:00:00Z', 'end_at': '2026-12-08T00:00:00Z'},
              'provenance_class': 'contemporaneous', 'rows': []}
    return {'record_id': 'a'*64, 'document': {'snapshot_id': saved['snapshot_id'], 'source': saved['source'],
            'input_hashes': {'baseline': 'd'*64}, 'enrolled_at': '2026-09-09T00:00:00Z',
            'production': deepcopy(stream), 'market': deepcopy(stream)}}


def _grade(saved, state='graded', horizon=90, evaluated_at='2026-12-09T00:00:00Z'):
    return {'record_id': 'b'*64, 'document': {'schema_version': 'track_record.grade.v1',
        'snapshot_id': saved['snapshot_id'], 'enrollment_id': 'a'*64, 'claim': 'market_movement',
        'horizon_days': horizon, 'decision_supported': False, 'policy_sha256': 'c'*64,
        'input_hashes': {'baseline': 'd'*64, 'outcome': 'e'*64}, 'outcome_source_hashes': {'outcome':'e'*64},
        'evaluated_at': evaluated_at, 'state': state, 'reason': 'Measured.' if state == 'graded' else 'Waiting.',
        'window': {'label': f'{horizon} days', 'start_at': '2026-09-09T00:00:00Z', 'end_at': '2026-12-08T00:00:00Z'},
        'provenance_class': 'contemporaneous', 'counts': {'eligible': 40, 'scored': 40, 'missing': 0},
        'result': {'summary': f'{horizon}-day result', 'comparisons': [], 'rows': [], 'details': []} if state == 'graded' else None}}


def test_waiting_record_does_not_hide_a_mature_grade(setup):
    saved = _saved(setup)
    enrollment = _enrollment(saved)
    pending = _grade(saved, state='awaiting_horizon', evaluated_at='2026-09-10T00:00:00Z')
    mature = _grade(saved)
    view = build_track_record_view(snapshots=[saved], enrollments=[enrollment], grades=[pending, mature], selected_snapshot_id=saved['snapshot_id'])
    assert view['market']['state'] == 'graded'
    assert view['market']['result']['summary'] == '90-day result'


def test_primary_90_day_grade_not_hidden_by_descriptive_30_day_grade(setup):
    saved = _saved(setup)
    enrollment = _enrollment(saved)
    short = _grade(saved, horizon=30, evaluated_at='2026-10-10T00:00:00Z')
    mature = _grade(saved)
    view = build_track_record_view(snapshots=[saved], enrollments=[enrollment], grades=[short, mature], selected_snapshot_id=saved['snapshot_id'])
    assert view['market']['result']['summary'] == '90-day result'


@pytest.mark.parametrize('mutation', ['no_outcome_binding', 'wrong_outcome_hash', 'empty_result', 'impossible_counts', 'boolean_estimate'])
def test_malformed_grades_refuse(setup, mutation):
    saved = _saved(setup)
    enrollment = _enrollment(saved)
    grade = _grade(saved)
    doc = grade['document']
    if mutation == 'no_outcome_binding':
        doc.pop('outcome_source_hashes')
    if mutation == 'wrong_outcome_hash':
        doc['outcome_source_hashes']['outcome'] = 'f'*64
    if mutation == 'empty_result':
        doc['result'] = {}
    if mutation == 'impossible_counts':
        doc['counts']['eligible'] = 1
    if mutation == 'boolean_estimate':
        doc['result']['comparisons'] = [{'id':'x','label':'x','units':'rho','estimate':True,'interval95':None,'state':'inconclusive','note':'x','eligible':40,'scored':40}]
    with pytest.raises(ValueError):
        build_track_record_view(snapshots=[saved], enrollments=[enrollment], grades=[grade], selected_snapshot_id=saved['snapshot_id'])
