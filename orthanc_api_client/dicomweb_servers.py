from typing import List, Union

from .exceptions import *
from .job import Job


class DicomWebServers:

    def __init__(self, api_client: 'OrthancApiClient'):
        self._api_client = api_client
        self._url_segment = 'dicom-web/servers'

    def stow_rs(self, target_server: str, resources_ids: Union[List[str], str], synchronous: bool = True):
        """alias for send"""
        return self.send(target_server=target_server, resources_ids=resources_ids, synchronous=synchronous)

    def send_asynchronous(self, target_server: str, resources_ids: Union[List[str], str]) -> Job:
        """sends a list of resources to a remote DicomWeb server

        Returns
        -------
        Nothing, will raise if failing 
        """

        if isinstance(resources_ids, str):
            resources_ids = [resources_ids]

        r = self._api_client.post(
            endpoint=f"{self._url_segment}/{target_server}/stow",
            json={
                "Resources": resources_ids,
                "Synchronous": False
            })

        return Job(api_client=self._api_client, orthanc_id=r.json()['ID'])
