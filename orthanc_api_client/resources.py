import requests
import logging
import typing

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

    def set_attachment(self, id, attachment_name, content = None, path = None, content_type = None, match_revision = None):
        
        if content is None and path is not None:
            with open(path, 'rb') as f:
                content = f.read()

        headers = {}

        if content_type:
            headers['Content-Type'] = content_type

        if match_revision:
            headers['If-Match'] = match_revision

        self._api_client.put(
            relative_url = f"/{self._url_segment}/{id}/attachments/{attachment_name}",
            data = content,
            headers = headers
        )

    def get_attachment(self, id, attachment_name) -> bytes:

        content, revision = self.get_attachment_with_revision(
            id=id,
            attachment_name=attachment_name
        )
        return content

    def get_attachment_with_revision(self, id, attachment_name) -> typing.Tuple[bytes, str]:

        headers = {}

        response = self._api_client.get(
            relative_url = f"/{self._url_segment}/{id}/attachments/{attachment_name}/data",
            headers = headers
        )

        return response.content, response.headers.get('etag')

    def download_attachment(self, id, attachment_name, path):
        content = self.get_attachment(id, attachment_name)

        with open(path, 'wb') as f:
            f.write(content)


    def set_metadata(self, id, metadata_name, content = None, path = None, match_revision = None):
        
        if content is None and path is not None:
            with open(path, 'rb') as f:
                content = f.read()

        headers = {}

        if match_revision:
            headers['If-Match'] = match_revision

        self._api_client.put(
            relative_url = f"/{self._url_segment}/{id}/metadata/{metadata_name}",
            data = content,
            headers = headers
        )


    def get_metadata(self, id, metadata_name) -> bytes:

        content, revision = self.get_metadata_with_revision(
            id=id,
            metadata_name=attachment_name
        )
        return content

    def get_metadata_with_revision(self, id, metadata_name) -> typing.Tuple[bytes, str]:

        headers = {}

        response = self._api_client.get(
            relative_url = f"/{self._url_segment}/{id}/metadata/{metadata_name}",
            headers = headers
        )

        return response.content, response.headers.get('etag')
