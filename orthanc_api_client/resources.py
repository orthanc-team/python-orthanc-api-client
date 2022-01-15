import requests
import logging
from typing import List, Tuple
from .exceptions import *



logger = logging.getLogger('api-client')


class Resources:

    def __init__(self, api_client: 'OrthancApiClient', url_segment: str):
        self._url_segment = url_segment
        self._api_client = api_client

    def get_all_ids(self) -> List[str]:
        return self._api_client.get_json(f"/{self._url_segment}/")

    def delete(self, orthanc_id: str = None, orthanc_ids: List[str] = None):

        if orthanc_ids:
            for oi in orthanc_ids:
                self.delete(orthanc_id=oi)

        if orthanc_id:
            logger.info(f"deleting {self._url_segment} {orthanc_id}")
            self._api_client.delete(f"/{self._url_segment}/{orthanc_id}")

    def delete_all(self) -> List[str]:
        all_ids = self.get_all_ids()
        deleted_ids = []

        for orthanc_id in all_ids:
            self.delete(orthanc_id)
            deleted_ids.append(orthanc_id)
        
        return deleted_ids

    def set_attachment(self, orthanc_id, attachment_name, content=None, path=None, content_type=None, match_revision=None):
        
        if content is None and path is not None:
            with open(path, 'rb') as f:
                content = f.read()

        headers = {}

        if content_type:
            headers['Content-Type'] = content_type

        if match_revision:
            headers['If-Match'] = match_revision

        self._api_client.put(
            relative_url=f"/{self._url_segment}/{orthanc_id}/attachments/{attachment_name}",
            data=content,
            headers=headers
        )

    def get_attachment(self, orthanc_id, attachment_name) -> bytes:

        content, revision = self.get_attachment_with_revision(
            orthanc_id=orthanc_id,
            attachment_name=attachment_name
        )
        return content

    def get_attachment_with_revision(self, orthanc_id, attachment_name) -> Tuple[bytes, str]:

        headers = {}

        response = self._api_client.get(
            relative_url=f"/{self._url_segment}/{orthanc_id}/attachments/{attachment_name}/data",
            headers=headers
        )

        return response.content, response.headers.get('etag')

    def download_attachment(self, orthanc_id, attachment_name, path):
        content = self.get_attachment(orthanc_id, attachment_name)

        with open(path, 'wb') as f:
            f.write(content)

    def set_metadata(self, orthanc_id, metadata_name, content=None, path=None, match_revision=None):
        
        if content is None and path is not None:
            with open(path, 'rb') as f:
                content = f.read()

        headers = {}

        if match_revision:
            headers['If-Match'] = match_revision

        self._api_client.put(
            relative_url=f"/{self._url_segment}/{orthanc_id}/metadata/{metadata_name}",
            data=content,
            headers=headers
        )

    def get_metadata(self, orthanc_id, metadata_name, default_value=None) -> bytes:

        content, revision = self.get_metadata_with_revision(
            orthanc_id=orthanc_id,
            metadata_name=metadata_name,
            default_value=default_value
        )

        return content

    def get_metadata_with_revision(self, orthanc_id, metadata_name, default_value=None) -> Tuple[bytes, str]:

        headers = {}

        try:
            response = self._api_client.get(
                relative_url=f"/{self._url_segment}/{orthanc_id}/metadata/{metadata_name}",
                headers=headers
            )
        except ResourceNotFound:
            return default_value, None

        return response.content, response.headers.get('etag')
