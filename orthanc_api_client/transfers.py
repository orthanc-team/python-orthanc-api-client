from typing import List, Union

from .exceptions import *
from .job import Job
from .change import ResourceType


class Transfers:

    def __init__(self, api_client: 'OrthancApiClient'):
        self._api_client = api_client
        self._url_segment = 'transfers'

    def send(self, target_peer: str, resources_ids: Union[List[str], str], resource_type: ResourceType, compress: bool = True) -> Job:

        if isinstance(resources_ids, str):
            resources_ids = [resources_ids]

        payload_resources_ids = []
        for resource_id in resources_ids:
            payload_resources_ids.append({
                "Level": resource_type,
                "ID": resource_id
            })

        r = self._api_client.post(
            endpoint=f"{self._url_segment}/send",
            json={
                "Resources": payload_resources_ids,
                "Compression": "gzip" if compress else "none",
                "Peer": target_peer
            })

        return Job(api_client=self._api_client, orthanc_id=r.json()['ID'])
