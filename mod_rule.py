from .setup import *
from .engine import score_filename


class ModuleRule(PluginModuleBase):

    def __init__(self, P):
        super(ModuleRule, self).__init__(P, name='rule', first_menu='setting')
        self.db_default = {
            f'{self.name}_db_version': '1',
            'rule_preferred_release_groups': 'F1RST|ST|KN|SW',
            'rule_preferred_sources': 'WEB-DL|NF|AMZN|DSNP|HDTV',
            'rule_preferred_resolutions': '2160p|1080p|720p|480p',
            'rule_ignore_single_candidates': 'True',
            'rule_group_by_plex_metadata_first': 'True',
            'rule_filename_sample': '이웃집 찰스.E521.260310.1080p-ST.mp4\n이웃집 찰스.E521.260310.1080p-SW.mp4',
        }


    def process_command(self, command, arg1, arg2, arg3, req):
        ret = {'ret': 'success'}
        if command == 'preview':
            raw = req.form.get('sample') or P.ModelSetting.get('rule_filename_sample')
            lines = [line.strip() for line in raw.splitlines() if line.strip()]
            ret['items'] = [
                score_filename(
                    line,
                    preferred_release=P.ModelSetting.get('rule_preferred_release_groups'),
                    preferred_source=P.ModelSetting.get('rule_preferred_sources'),
                    preferred_resolution=P.ModelSetting.get('rule_preferred_resolutions'),
                )
                for line in lines
            ]
            ret['msg'] = '파일명 미리보기를 계산했습니다.'
        return jsonify(ret)
