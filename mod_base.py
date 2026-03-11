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
        return jsonify(ret)
