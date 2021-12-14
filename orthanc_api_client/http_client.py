from typing import Any
import requests
import urllib.parse

from orthanc_api_client import exceptions as api_exceptions


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

    def get(self, relative_url: str, **kwargs) -> requests.Response:
        try:
            url = self.get_abs_url(relative_url)
            response = self._http_session.get(url, **kwargs)
        except requests.RequestException as request_exception:
            self._translate_exception(request_exception, url=url)
        
        self._raise_on_errors(response, url = url)
        return response

    def get_json(self, relative_url: str, **kwargs) -> Any:
        return self.get(relative_url, **kwargs).json()

    def get_binary(self, relative_url: str, **kwargs) -> Any:
        return self.get(relative_url, **kwargs).content

    def post(self, relative_url: str, **kwargs) -> requests.Response:
        try:
            url = self.get_abs_url(relative_url)
            response = self._http_session.post(url, **kwargs)
        except requests.RequestException as request_exception:
            self._translate_exception(request_exception, url=url)
        
        self._raise_on_errors(response, url=url)
        return response

    def put(self, relative_url: str, **kwargs) -> requests.Response:
        try:
            url = self.get_abs_url(relative_url)
            response = self._http_session.put(url, **kwargs)
        except requests.RequestException as request_exception:
            self._translate_exception(request_exception, url=url)
        
        self._raise_on_errors(response, url=url)
        return response

    def delete(self, relative_url: str, **kwargs) -> requests.Response:
        try:
            url = self.get_abs_url(relative_url)
            response = self._http_session.delete(url, **kwargs)
        except requests.RequestException as request_exception:
            self._translate_exception(request_exception, url=url)
        
        self._raise_on_errors(response, url = url)
        return response

    def _raise_on_errors(self, response, url):
        if response.status_code == 200:
            return

        if response.status_code == 401:
            raise api_exceptions.NotAuthorized(response.status_code, url=url)
        elif response.status_code == 404:
            raise api_exceptions.ResourceNotFound(response.status_code, url=url)
        else:
            raise api_exceptions.HttpError(response.status_code, url=url, request_response=response)

    def _translate_exception(self, request_exception, url):
        if isinstance(request_exception, requests.ConnectionError):
            raise api_exceptions.ConnectionError(url=url)
        elif isinstance(request_exception, requests.Timeout):
            raise api_exceptions.TimeoutError(url=url)
        elif isinstance(request_exception, requests.SSLError):
            raise api_exceptions.SSLError(url=url)
