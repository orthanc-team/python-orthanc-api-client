from typing import Any
import requests
import urllib.parse

from orthanc_api_client import exceptions as api_exceptions


class HttpClient:

    def __init__(self, root_url: str, user: str = None, pwd: str = None, headers: any = None) -> None:
        self._root_url = root_url
        self._http_session = requests.Session()

        if user and pwd:
            self._http_session.auth = requests.auth.HTTPBasicAuth(user, pwd)
        if headers:
            self._http_session.headers.update(headers)

        self._user = user
        self._pwd = pwd

    def get_abs_url(self, endpoint: str) -> str:
        return urllib.parse.urljoin(self._root_url, endpoint)

    def get(self, endpoint: str, **kwargs) -> requests.Response:
        try:
            url = self.get_abs_url(endpoint)
            response = self._http_session.get(url, **kwargs)
        except requests.RequestException as request_exception:
            self._translate_exception(request_exception, url=url)

        self._raise_on_errors(response, url=url)
        return response

    def get_json(self, endpoint: str, **kwargs) -> Any:
        return self.get(endpoint, **kwargs).json()

    def get_binary(self, endpoint: str, **kwargs) -> Any:
        return self.get(endpoint, **kwargs).content

    def post(self, endpoint: str, **kwargs) -> requests.Response:
        try:
            url = self.get_abs_url(endpoint)
            response = self._http_session.post(url, **kwargs)
        except requests.RequestException as request_exception:
            self._translate_exception(request_exception, url=url)

        self._raise_on_errors(response, url=url)
        return response

    def put(self, endpoint: str, **kwargs) -> requests.Response:
        try:
            url = self.get_abs_url(endpoint)
            response = self._http_session.put(url, **kwargs)
        except requests.RequestException as request_exception:
            self._translate_exception(request_exception, url=url)

        self._raise_on_errors(response, url=url)
        return response

    def delete(self, endpoint: str, **kwargs) -> requests.Response:
        try:
            url = self.get_abs_url(endpoint)
            response = self._http_session.delete(url, **kwargs)
        except requests.RequestException as request_exception:
            self._translate_exception(request_exception, url=url)

        self._raise_on_errors(response, url=url)
        return response

    def close(self):
        self._http_session.close()

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def __del__(self):
        self.close()

    def _raise_on_errors(self, response, url):
        if response.status_code >= 200 and response.status_code < 300:
            return

        if response.status_code == 401:
            raise api_exceptions.NotAuthorized(response.status_code, url=url)
        elif response.status_code == 404:
            raise api_exceptions.ResourceNotFound(
                response.status_code, url=url)
        else:
            raise api_exceptions.HttpError(
                response.status_code, url=url, request_response=response)

    def _translate_exception(self, request_exception, url):
        if isinstance(request_exception, requests.ConnectionError):
            raise api_exceptions.ConnectionError(url=url)
        elif isinstance(request_exception, requests.Timeout):
            raise api_exceptions.TimeoutError(url=url)
        elif isinstance(request_exception, requests.SSLError):
            raise api_exceptions.SSLError(url=url)
