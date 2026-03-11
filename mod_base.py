from .setup import *


class ModuleBase(PluginModuleBase):

    def __init__(self, P):
        super(ModuleBase, self).__init__(P, name='base', first_menu='setting')
        self.db_default = {
            f'{self.name}_db_version': '1',
            'base_plex_db_path': '',
            'base_plex_url': 'http://127.0.0.1:32400',
            'base_plex_token': '',
            'base_storage_db_path': '',
            'base_target_sections': '',
            'base_library_root_hint': '',
            'base_use_plex_db': 'True',
            'base_use_plex_web': 'True',
            'base_plugin_note': 'bot_log_monitor keeps downloading. plex_curator evaluates duplicates after Plex indexing.',
        }


    def _get_plex_mate_settings(self, include_token=True):
        ret = {
            'ret': 'fail',
            'msg': 'plex_mate 설정을 찾을 수 없습니다.',
            'data': {},
        }
        try:
            framework = globals().get('F')
            if framework is None or getattr(framework, 'PluginManager', None) is None:
                ret['msg'] = '플러그인 매니저를 찾을 수 없습니다.'
                return ret
            plugin_instance = framework.PluginManager.get_plugin_instance('plex_mate')
            model_setting = getattr(plugin_instance, 'ModelSetting', None)
            if model_setting is None:
                return ret

            plex_db_path = model_setting.get('base_path_db')
            plex_url = model_setting.get('base_url') or model_setting.get('base_plex_url')
            plex_token = model_setting.get('base_token') if include_token else ''
            library_root_hint = model_setting.get('base_path_media')

            ret['ret'] = 'success'
            ret['msg'] = 'plex_mate 설정을 읽었습니다.'
            ret['data'] = {
                'plex_db_path': plex_db_path or '',
                'plex_url': plex_url or '',
                'plex_token': plex_token or '',
                'library_root_hint': library_root_hint or '',
            }
            return ret
        except Exception as e:
            ret['msg'] = f'plex_mate 설정 읽기 실패: {str(e)}'
            return ret


    def process_command(self, command, arg1, arg2, arg3, req):
        ret = {}
        ret['ret'] = 'success'
        if command == 'validate':
            ret['msg'] = '기본 설정 검증은 다음 단계에서 구현 예정입니다.'
            ret['data'] = {
                'plex_db_path': P.ModelSetting.get('base_plex_db_path'),
                'storage_db_path': P.ModelSetting.get('base_storage_db_path'),
                'plex_url': P.ModelSetting.get('base_plex_url'),
                'use_plex_db': P.ModelSetting.get_bool('base_use_plex_db'),
                'use_plex_web': P.ModelSetting.get_bool('base_use_plex_web'),
            }
        elif command == 'load_plex_mate':
            ret = self._get_plex_mate_settings(include_token=True)
            if ret.get('ret') == 'success':
                data = ret.get('data', {})
                if data.get('plex_db_path'):
                    P.ModelSetting.set('base_plex_db_path', data.get('plex_db_path', ''))
                if data.get('plex_url'):
                    P.ModelSetting.set('base_plex_url', data.get('plex_url', ''))
                if data.get('plex_token'):
                    P.ModelSetting.set('base_plex_token', data.get('plex_token', ''))
                if data.get('library_root_hint'):
                    P.ModelSetting.set('base_library_root_hint', data.get('library_root_hint', ''))
                ret['msg'] = 'plex_mate 설정을 현재 plex_curator 설정에 반영했습니다. 비어 있던 값만 자동 채움은 페이지 로드에서 동작하고, 이 버튼은 사용 가능한 값만 즉시 가져옵니다.'
        elif command == 'peek_plex_mate':
            ret = self._get_plex_mate_settings(include_token=False)
        return jsonify(ret)
