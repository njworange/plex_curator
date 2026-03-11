import requests


class PlexWebAdapter(object):
    def __init__(self, base_url, token):
        self.base_url = (base_url or '').rstrip('/')
        self.token = token or ''

    def is_available(self):
        return bool(self.base_url and self.token)

    def _params(self, extra=None):
        data = {'X-Plex-Token': self.token}
        if extra:
            data.update(extra)
        return data

    def ping(self):
        if not self.is_available():
            return {'ret': 'fail', 'msg': 'Plex Web adapter unavailable'}
        try:
            response = requests.get(f'{self.base_url}/identity', params=self._params(), timeout=10)
            return {'ret': 'success', 'status_code': response.status_code, 'text': response.text[:200]}
        except Exception as e:
            return {'ret': 'fail', 'msg': str(e)}

    def refresh_metadata(self, rating_key):
        if not self.is_available():
            return {'ret': 'fail', 'msg': 'Plex Web adapter unavailable'}
        try:
            response = requests.put(f'{self.base_url}/library/metadata/{rating_key}/refresh', params=self._params(), timeout=20)
            return {'ret': 'success', 'status_code': response.status_code}
        except Exception as e:
            return {'ret': 'fail', 'msg': str(e)}
