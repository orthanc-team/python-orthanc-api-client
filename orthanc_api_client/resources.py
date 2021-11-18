import requests
import logging

from typing import List
from .http_client import HttpClient


logger = logging.getLogger('api-client')


class Resources:

    def __init__(self, http_client: HttpClient, url_segment: str):
        self._url_segment = url_segment
        self._http_client = http_client

    def get_all_ids(self) -> List[str]:
        return self._http_client.get_json(f"/{self._url_segment}/")

    def delete_all(self) -> List[str]:
        all_ids = self.get_all_ids()
        deleted_ids = []

        for id in all_ids:
            logger.info(f"deleting {self._url_segment} {id}")
            self._http_client.delete(f"/{self._url_segment}/{id}")
            deleted_ids.append(id)
        
        return deleted_ids