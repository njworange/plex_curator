from .setup import *
from .adapter_plex_web import PlexWebAdapter
from .pipeline import run_dry_curator
from .storage import RunStore, get_db_path, init_db


class ModuleTask(PluginModuleBase):

    def __init__(self, P):
        super(ModuleTask, self).__init__(P, name='task', first_menu='setting')
        self.db_default = {
            f'{self.name}_db_version': '1',
            'task_run_mode': 'log_only',
            'task_debug_logging': 'True',
            'task_schedule_cron': '',
            'task_scan_after_refresh': 'True',
            'task_require_manual_review': 'True',
            'task_delete_action': 'trash',
            'task_last_preview': '',
        }


    def process_command(self, command, arg1, arg2, arg3, req):
        if command == 'run_dry':
            db_path = get_db_path(P.ModelSetting.get('base_storage_db_path'))
            settings = {
                'storage_db_path': db_path,
                'run_mode': P.ModelSetting.get('task_run_mode'),
                'plex_db_path': P.ModelSetting.get('base_plex_db_path'),
                'target_sections': P.ModelSetting.get('base_target_sections'),
                'preferred_release': P.ModelSetting.get('rule_preferred_release_groups'),
                'preferred_source': P.ModelSetting.get('rule_preferred_sources'),
                'preferred_resolution': P.ModelSetting.get('rule_preferred_resolutions'),
                'metadata_first': P.ModelSetting.get_bool('rule_group_by_plex_metadata_first'),
                'ignore_single': P.ModelSetting.get_bool('rule_ignore_single_candidates'),
                'use_plex_db': P.ModelSetting.get_bool('base_use_plex_db'),
                'use_plex_web': P.ModelSetting.get_bool('base_use_plex_web'),
                'scan_after_refresh': P.ModelSetting.get_bool('task_scan_after_refresh'),
                'require_manual_review': P.ModelSetting.get_bool('task_require_manual_review'),
                'delete_action': P.ModelSetting.get('task_delete_action'),
                'debug_logging': P.ModelSetting.get_bool('task_debug_logging'),
                'logger': getattr(P, 'logger', None),
            }
            init_db(db_path)
            ret = run_dry_curator(settings)
            if ret.get('ret') == 'success':
                P.ModelSetting.set('result_last_run_summary', str(ret.get('summary', {})))
                P.ModelSetting.set('task_last_preview', str(ret.get('run_id', '')))
            return jsonify(ret)
        elif command == 'run_review':
            return jsonify({'ret': 'success', 'msg': '리뷰 큐는 결과 메뉴에서 승인/보류 상태를 바꾸며 운영합니다.'})
        elif command == 'status':
            db_path = get_db_path(P.ModelSetting.get('base_storage_db_path'))
            runs = RunStore.list_recent(db_path=db_path)
            latest_run = runs[0] if runs else None
            return jsonify({'ret': 'success', 'runs': runs, 'latest_run': latest_run})
        elif command == 'ping_plex':
            adapter = PlexWebAdapter(P.ModelSetting.get('base_plex_url'), P.ModelSetting.get('base_plex_token'))
            return jsonify(adapter.ping())
        return jsonify({'ret': 'success'})
