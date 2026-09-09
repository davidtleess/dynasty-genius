"""Private local track-record view; saving always preserves the exact displayed sources."""
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from app.api.routes import workspace_snapshots as archive
from src.dynasty_genius.adapters.track_record_view import (
    build_track_record_view,
    safe_receipt,
)
from src.dynasty_genius.capture.workspace_snapshot_store import strict_json

router = APIRouter(prefix='/research/track-record')


def _evaluation_records(snapshot_ids):
    location = os.environ.get('DG_EVALUATION_ROOT')
    if not location:
        return [], []
    from src.dynasty_genius.capture.track_record_store import list_records
    records = [record for sid in snapshot_ids for record in list_records(Path(location), snapshot_id=sid)]
    return [r for r in records if r['kind'] == 'enrollment'], [r for r in records if r['kind'] == 'grade']


def _save_capability():
    if archive._root() is None:
        return {'enabled': False, 'reason': 'Saving is not configured in this session.', 'expected': None}
    try:
        current = archive.load_workspace_snapshot(*archive._current_paths())
        return {'enabled': True, 'reason': None, 'expected': archive._source(current)}
    except (OSError, ValueError, KeyError, TypeError, HTTPException):
        return {'enabled': False, 'reason': 'Current board sources could not be verified. Saved readings remain available.', 'expected': None}


def _unavailable():
    return HTTPException(503, 'The saved readings or evaluation inputs could not be verified. No other reading was substituted.')


@router.get('')
def track_record(snapshot_id: str | None = Query(default=None, pattern=r'^[a-f0-9]{64}$')):
    try:
        root = archive._root()
        snapshots = archive.list_snapshots(root) if root is not None else []
        if snapshot_id and snapshot_id not in {s['snapshot_id'] for s in snapshots}:
            raise HTTPException(404, 'This saved reading was not found.')
        enrollments, grades = _evaluation_records([s['snapshot_id'] for s in snapshots])
        view = build_track_record_view(snapshots=snapshots, enrollments=enrollments, grades=grades, selected_snapshot_id=snapshot_id)
        if root is None:
            view['status'] = 'not_configured'
            view['reason'] = 'Saved readings are not connected in this session.'
        view['save_capability'] = _save_capability()
        return view
    except (OSError, ValueError, KeyError, TypeError, ImportError):
        raise _unavailable() from None


def _enroll_saved(snapshot_id):
    config_path = os.environ.get('DG_TRACK_RECORD_INPUTS_CONFIG')
    evaluation_root = os.environ.get('DG_EVALUATION_ROOT')
    if not config_path or not evaluation_root:
        return None
    path = Path(config_path)
    if not path.is_absolute() or path.is_symlink():
        raise ValueError('Explicit real configuration path required')
    config = strict_json(path.read_bytes(), 'track record source configuration')
    required = {'baseline_manifest', 'baseline_csv', 'baseline_receipt', 'schedule', 'market_plan'}
    if not isinstance(config, dict) or set(config) - required - {'market_history'} or not required <= set(config):
        raise ValueError('Incomplete source configuration')
    for value in config.values():
        if value is not None and (not isinstance(value, str) or not Path(value).is_absolute()):
            raise ValueError('Explicit absolute source paths required')
    from scripts.capture_track_record_inputs import capture_from_paths
    return capture_from_paths(archive_root=archive._root(), snapshot_id=snapshot_id, evaluation_root=Path(evaluation_root), **{key: Path(value) if value else None for key, value in config.items()})


@router.post('/capture')
def capture(request: archive.SaveRequest):
    saved = archive.capture(request)
    receipt = safe_receipt(saved['snapshot'])
    response = {'snapshot_status': 'saved' if saved['created'] else 'already_saved', 'snapshot': receipt, 'enrollment_status': 'input_unavailable', 'reason': 'Your reading is saved. Evaluation baselines are not connected yet.'}
    try:
        enrollment = _enroll_saved(receipt['snapshot_id'])
        if enrollment is not None:
            response['enrollment_status'] = 'saved' if enrollment['created'] else 'already_saved'
            document = enrollment['record']['document']
            gaps = [document[key]['reason'] for key in ('production', 'market') if document[key]['state'] in {'not_registered', 'input_unavailable', 'cutoff_ineligible'}]
            response['reason'] = ('Your reading is saved. ' + ' '.join(gaps)) if gaps else None
    except (OSError, ValueError, KeyError, TypeError, ImportError):
        response['reason'] = 'Your reading is saved. Its evaluation inputs could not be verified; they have not been reported as saved.'
    return response
