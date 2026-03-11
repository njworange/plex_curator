import traceback

setting = {
    'filepath': __file__,
    'use_db': True,
    'use_default_setting': True,
    'home_module': None,
    'menu': {
        'uri': __package__,
        'name': 'Plex Curator',
        'list': [
            {
                'uri': 'base',
                'name': '기본',
                'list': [
                    {'uri': 'setting', 'name': '설정'},
                ],
            },
            {
                'uri': 'rule',
                'name': '정책',
                'list': [
                    {'uri': 'setting', 'name': '설정'},
                ],
            },
            {
                'uri': 'task',
                'name': '실행',
                'list': [
                    {'uri': 'setting', 'name': '설정'},
                ],
            },
            {
                'uri': 'result',
                'name': '결과',
                'list': [
                    {'uri': 'setting', 'name': '설명'},
                ],
            },
            {
                'uri': 'manual',
                'name': '매뉴얼',
                'list': [
                    {'uri': 'README.md', 'name': 'README.md'},
                ],
            },
            {
                'uri': 'log',
                'name': '로그',
            },
        ],
    },
    'setting_menu': None,
    'default_route': 'normal',
}

from .compat import *

P = create_plugin_instance(setting)

try:
    from .mod_base import ModuleBase
    from .mod_rule import ModuleRule
    from .mod_task import ModuleTask
    from .mod_result import ModuleResult

    P.set_module_list([ModuleBase, ModuleRule, ModuleTask, ModuleResult])
except Exception as e:
    P.logger.error(f'Exception:{str(e)}')
    P.logger.error(traceback.format_exc())

logger = P.logger
