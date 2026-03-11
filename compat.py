import traceback

try:
    from flask import jsonify
except Exception:
    def jsonify(data):
        return data

try:
    from flask import render_template
except Exception:
    def render_template(template_name, **kwargs):
        return {'template': template_name, 'context': kwargs}


class PluginModuleBase(object):
    def __init__(self, P, name='', first_menu='setting'):
        self.P = P
        self.name = name
        self.first_menu = first_menu
        self.db_default = {}


class PluginPageBase(object):
    def __init__(self, P, parent, name='setting'):
        self.P = P
        self.parent = parent
        self.name = name
        self.db_default = {}


class _DummyLogger(object):
    def info(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        pass


class _DummyModelSetting(object):
    _data = {}

    @classmethod
    def get(cls, key):
        return cls._data.get(key, '')

    @classmethod
    def get_bool(cls, key):
        value = cls._data.get(key, 'False')
        if isinstance(value, bool):
            return value
        return str(value).lower() == 'true'

    @classmethod
    def set(cls, key, value):
        cls._data[key] = value


class _DummyPlugin(object):
    logger = _DummyLogger()
    ModelSetting = _DummyModelSetting()
    package_name = 'plex_curator'

    def set_module_list(self, module_list):
        self.module_list = module_list


def default_route_socketio_page(page):
    return page


def create_plugin_instance(setting):
    return _DummyPlugin()


try:
    from plugin import *  # type: ignore
except Exception:
    pass
