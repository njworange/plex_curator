import os

from .adapter_plex_db import PlexDbAdapter
from .engine import score_filename, normalize_title
from .storage import CandidateStore, DecisionStore, GroupStore, RunStore, init_db


def _build_metadata_group_key(row, scored):
    metadata_type = row.get('metadata_type')
    if metadata_type == 4:
        show_title = row.get('grandparent_title') or row.get('parent_title') or scored.get('title')
        season_index = row.get('parent_index')
        item_index = row.get('item_index')
        if season_index not in [None, ''] and item_index not in [None, '', -1]:
            return f"tv|{normalize_title(show_title)}|s{season_index}|e{item_index}"
    elif metadata_type == 1:
        movie_title = row.get('item_title') or scored.get('title')
        year = row.get('item_year') or ''
        if movie_title:
            return f"movie|{normalize_title(movie_title)}|{year}"
    return scored.get('group_key')


def _coerce_action(mode, delete_action, require_manual_review, is_winner, duplicate_group):
    if is_winner:
        return ('keep', 'highest score in group', 'planned')
    if not duplicate_group:
        return ('keep', 'single candidate group', 'planned')
    if mode == 'log_only':
        return ('hold', 'log-only mode keeps losers for inspection', 'planned')
    if require_manual_review:
        return (delete_action or 'trash', 'manual review required before destructive action', 'pending_review')
    if mode == 'delete':
        return (delete_action or 'trash', 'automatic destructive mode enabled', 'planned')
    if mode == 'review':
        return (delete_action or 'trash', 'review mode requires operator approval', 'pending_review')
    return ('hold', 'fallback hold action', 'planned')


def analyze_candidates(candidates, preferred_release='', preferred_source='', preferred_resolution='', metadata_first=True, ignore_single=False, run_mode='log_only', delete_action='trash', require_manual_review=True):
    grouped = {}
    for row in candidates:
        filepath = row.get('file_path') or ''
        filename = os.path.basename(filepath)
        scored = score_filename(
            filename,
            preferred_release=preferred_release,
            preferred_source=preferred_source,
            preferred_resolution=preferred_resolution,
        )
        media_type = 'movie' if row.get('metadata_type') == 1 else 'show'
        if metadata_first:
            group_key = _build_metadata_group_key(row, scored)
        else:
            group_key = scored.get('group_key')
        candidate = {
            'plex_rating_key': row.get('metadata_id'),
            'plex_media_part_id': row.get('media_part_id'),
            'media_type': media_type,
            'section_name': row.get('section_name') or '',
            'title': row.get('item_title') or row.get('parent_title') or row.get('grandparent_title') or scored.get('title'),
            'filename': filename,
            'filepath': filepath,
            'release_group': scored.get('release_group'),
            'resolution': scored.get('resolution'),
            'codec': scored.get('codec'),
            'sources': scored.get('sources'),
            'group_key': group_key,
            'score': scored.get('score', 0),
            'metadata': row,
        }
        grouped.setdefault(group_key, []).append(candidate)

    for group_key in grouped:
        grouped[group_key].sort(key=lambda item: (-item['score'], item['filename']))
        if grouped[group_key]:
            grouped[group_key][0]['is_winner'] = True
        duplicate_group = len(grouped[group_key]) > 1
        for item in grouped[group_key]:
            planned_action, action_reason, action_status = _coerce_action(
                run_mode,
                delete_action,
                require_manual_review,
                item.get('is_winner', False),
                duplicate_group,
            )
            item['planned_action'] = planned_action
            item['action_reason'] = action_reason
            item['action_status'] = action_status
            if ignore_single and not duplicate_group:
                item['planned_action'] = 'ignore'
                item['action_reason'] = 'single candidate ignored by policy'
                item['action_status'] = 'ignored'
    return grouped


def _make_debugger(settings, debug_lines):
    def debug(message):
        line = str(message)
        debug_lines.append(line)
        logger = settings.get('logger')
        if settings.get('debug_logging', True) and logger is not None:
            try:
                logger.warning(f'[plex_curator] {line}')
            except Exception:
                pass
    return debug


def run_dry_curator(settings):
    db_path = settings.get('storage_db_path', '')
    init_db(db_path)
    debug_lines = []
    debug = _make_debugger(settings, debug_lines)
    debug(f'Run start: mode={settings.get("run_mode", "log_only")}, storage_db={db_path}')
    run_id = RunStore.create(
        mode=settings.get('run_mode', 'log_only'),
        status='running',
        plex_db_path=settings.get('plex_db_path', ''),
        target_sections=settings.get('target_sections', ''),
        summary={'stage': 'starting', 'debug_lines': debug_lines},
        db_path=db_path,
    )
    try:
        if not settings.get('use_plex_db', True):
            debug('Dry run aborted because Plex DB usage is disabled')
            raise Exception('Plex DB usage is disabled by settings')
        adapter = PlexDbAdapter(settings.get('plex_db_path', ''))
        debug(f'Plex DB path configured: {settings.get("plex_db_path", "") or "(empty)"}')
        candidates = adapter.fetch_media_candidates(settings.get('target_sections', ''), debug_callback=debug) if adapter.is_available() else []
        if not adapter.is_available():
            debug('Adapter reported Plex DB unavailable; candidate list will be empty')
        grouped = analyze_candidates(
            candidates,
            preferred_release=settings.get('preferred_release', ''),
            preferred_source=settings.get('preferred_source', ''),
            preferred_resolution=settings.get('preferred_resolution', ''),
            metadata_first=settings.get('metadata_first', True),
            ignore_single=settings.get('ignore_single', False),
            run_mode=settings.get('run_mode', 'log_only'),
            delete_action=settings.get('delete_action', 'trash'),
            require_manual_review=settings.get('require_manual_review', True),
        )
        debug(f'Grouped candidates: {len(grouped)} groups from {len(candidates)} candidates')

        warnings = []
        if settings.get('scan_after_refresh') and not settings.get('use_plex_web', False):
            warnings.append('scan_after_refresh requested but Plex Web usage is disabled')
        if settings.get('run_mode') == 'delete' and settings.get('require_manual_review', True):
            warnings.append('delete mode downgraded to review actions because manual review is required')

        summary = {
            'candidate_total': len(candidates),
            'group_total': len(grouped),
            'duplicate_group_total': len([key for key, items in grouped.items() if len(items) > 1]),
            'ignored_single_group_total': len([key for key, items in grouped.items() if len(items) == 1 and settings.get('ignore_single', False)]),
            'warnings': warnings,
            'debug_lines': debug_lines,
        }
        if len(candidates) == 0:
            debug('No Plex candidates found. Check DB path, section filter, and DB access settings.')
        for group_key, items in grouped.items():
            rationale = 'single candidate' if len(items) == 1 else 'score based winner selected'
            debug(f'Persist group: {group_key} ({len(items)} candidates)')
            group_id = GroupStore.create(
                run_id=run_id,
                media_type=items[0].get('media_type', ''),
                section_name=items[0].get('section_name', ''),
                group_key=group_key,
                candidate_count=len(items),
                rationale=rationale,
                db_path=db_path,
            )
            winner_id = None
            for item in items:
                candidate_id = CandidateStore.create(run_id, group_id, item, db_path=db_path)
                if item.get('is_winner'):
                    winner_id = candidate_id
                item['candidate_id'] = candidate_id
            if winner_id is not None:
                if len(items) == 1 and settings.get('ignore_single', False):
                    review_status = 'ignored'
                elif settings.get('require_manual_review', True) and len(items) > 1:
                    review_status = 'pending_review'
                else:
                    review_status = 'pending'
                GroupStore.set_winner(group_id, winner_id, review_status=review_status, db_path=db_path)
            DecisionStore.create(run_id, group_id, 'analyzed', note=rationale, payload={'candidate_count': len(items), 'warnings': warnings}, db_path=db_path)

        RunStore.update(run_id, status='completed', summary=summary, db_path=db_path)
        debug(f'Run complete: run_id={run_id}')
        return {'ret': 'success', 'run_id': run_id, 'summary': summary, 'debug_lines': debug_lines, 'msg': f'Dry run completed. candidates={len(candidates)}, groups={len(grouped)}'}
    except Exception as e:
        debug(f'Run failed: {str(e)}')
        RunStore.update(run_id, status='failed', error_text=str(e), summary={'stage': 'failed', 'debug_lines': debug_lines}, db_path=db_path)
        return {'ret': 'fail', 'run_id': run_id, 'msg': str(e), 'debug_lines': debug_lines}
