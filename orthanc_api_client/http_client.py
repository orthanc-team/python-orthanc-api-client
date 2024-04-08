from typing import Any
import requests
import urllib.parse
import json
from requests.adapters import HTTPAdapter, Retry

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

        # only retries on ConnectionError and on Transient errors when we are sure that the request has not reached to Orthanc
        retries = Retry(  # doc: https://urllib3.readthedocs.io/en/stable/reference/urllib3.util.html#urllib3.util.Retry
            connect=3,
            read=3,
            status=3,
            allowed_methods=frozenset({'DELETE', 'GET', 'HEAD', 'OPTIONS', 'PUT', 'TRACE', 'POST'}), # allow "POST" because we retry only when the request has not reached Orthanc !
            status_forcelist=frozenset({502, 503}),  # only retry "Bad Gateway" and "Service Unavailable"
            backoff_factor=0.2
        )
        url_schema = urllib.parse.urlparse(root_url).scheme + "://"
        self._http_session.mount(url_schema, HTTPAdapter(max_retries=retries))


    def get_abs_url(self, endpoint: str) -> str:
        # remove the leading '/' because _root_url might be something like 'http://my.domain/orthanc/' and urljoin would then remove the '/orthanc'
        normalised_endpoint = endpoint[1:] if endpoint.startswith("/") else endpoint

        return urllib.parse.urljoin(self._root_url, normalised_endpoint)


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
        elif response.status_code == 409:
            raise api_exceptions.Conflict(
                msg=response.json()['Message'] if response.json() and 'Message' in response.json() else None,
                url=url
            )
        else:
            error_messages = []
            error_message = None
            # try to get details from the payload
            if len(response.content) > 0:
                try:
                    payload = json.loads(response.content)
                    if 'Message' in payload:
                        error_messages.append(payload['Message'])
                    if 'Details' in payload and len(payload['Details']) > 0:
                        error_messages.append(payload['Details'])
                except:
                    pass

            if len(error_messages) > 0:
                error_message = " - ".join(error_messages)
            raise api_exceptions.HttpError(
                http_status_code=response.status_code,
                msg=error_message,
                url=url,
                request_response=response)

    def _translate_exception(self, request_exception, url):
        if isinstance(request_exception, requests.ConnectionError):
            raise api_exceptions.ConnectionError(url=url)
        elif isinstance(request_exception, requests.Timeout):
            raise api_exceptions.TimeoutError(url=url)
        elif isinstance(request_exception, requests.exceptions.SSLError):
            raise api_exceptions.SSLError(url=url)
