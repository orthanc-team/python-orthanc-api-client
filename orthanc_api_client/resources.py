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

    def set_attachment(self, id, attachment_name, content = None, path = None, content_type = None):
        if content is None and path is not None:
            with open(path, 'rb') as f:
                content = f.read()

        if content_type is not None:
            headers = {
                'Content-Type': content_type
            }
        else:
            headers = {}

        self._api_client.put(
            relative_url = f"/{self._url_segment}/{id}/attachments/{attachment_name}",
            data = content,
            headers = headers
        )

    def get_attachment(self, id, attachment_name) -> bytes:
        return self._api_client.get(
            relative_url = f"/{self._url_segment}/{id}/attachments/{attachment_name}/data"
        ).content

    def download_attachment(self, id, attachment_name, path):
        content = self.get_attachment(id, attachment_name)

        with open(path, 'wb') as f:
            f.write(content)
