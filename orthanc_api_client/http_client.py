from typing import Any
import requests
import urllib.parse

class HttpClient:

    def __init__(self, root_url: str, user: str = None, pwd: str = None) -> None:
        self._root_url = root_url
        self._http_session = requests.Session()

        if user and pwd:
            self._http_session.auth = requests.auth.HTTPBasicAuth(user, pwd)

        self._user = user
        self._pwd = pwd

    def get_abs_url(self, relative_url: str) -> str:
        return urllib.parse.urljoin(self._root_url, relative_url)

    def get(self, relative_url: str) -> requests.Response:
        return self._http_session.get(self.get_abs_url(relative_url))

    def get_json(self, relative_url: str) -> Any:
        return self.get(relative_url).json()

    def get_binary(self, relative_url: str) -> Any:
        return self.get(relative_url).content

    def post(self, relative_url: str, data: Any) -> requests.Response:
        return self._http_session.post(self.get_abs_url(relative_url), data=data)