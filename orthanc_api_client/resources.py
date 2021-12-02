import requests
import logging

from typing import List


logger = logging.getLogger('api-client')


class Resources:

    def __init__(self, api_client: 'OrthancApiClient', url_segment: str):
        self._url_segment = url_segment
        self._api_client = api_client

    def get_all_ids(self) -> List[str]:
        return self._api_client.get_json(f"/{self._url_segment}/")

    def delete_all(self) -> List[str]:
        all_ids = self.get_all_ids()
        deleted_ids = []

        for id in all_ids:
            logger.info(f"deleting {self._url_segment} {id}")
            self._api_client.delete(f"/{self._url_segment}/{id}")
            deleted_ids.append(id)
        
        return deleted_ids