from typing import List, Union

from .exceptions import *
from .job import Job
from .change import ResourceType


class Peers:

    def __init__(self, api_client: 'OrthancApiClient'):
        self._api_client = api_client
        self._url_segment = 'peers'

    def send_async(self, target_peer: str, resources_ids: Union[List[str], str]) -> Job :

        if isinstance(resources_ids, str):
            resources_ids = [resources_ids]

        payload_resources_ids = []
        for resource_id in resources_ids:
            payload_resources_ids.append(resource_id)

        r = self._api_client.post(
            endpoint=f"{self._url_segment}/{target_peer}/store",
            json= {
                "Resources": payload_resources_ids,
                "Synchronous": False
            })

        return Job(api_client=self._api_client, orthanc_id=r.json()['ID'])


    # sends a resource synchronously
    def send(self, target_peer: str, resources_ids: Union[List[str], str]):

        if isinstance(resources_ids, str):
            resources_ids = [resources_ids]

        payload_resources_ids = []
        for resource_id in resources_ids:
            payload_resources_ids.append(resource_id)

        self._api_client.post(
            endpoint=f"{self._url_segment}/{target_peer}/store",
            json= {
                "Resources": payload_resources_ids,
                "Synchronous": True
            })
