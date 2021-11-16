import requests
from typing import List
from .http_client import HttpClient

class Resources:

    def __init__(self, http_client: HttpClient, url_segment: str):
        self._url_segment = url_segment
        self._http_client = http_client

    def get_all_ids(self) -> List[str]:
        return self._http_client.get_json(f"/{self._url_segment}/")

