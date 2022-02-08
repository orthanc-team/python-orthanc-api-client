from typing import List, Union

from .exceptions import *


class DicomModalities:

    def __init__(self, api_client: 'OrthancApiClient'):
        self._api_client = api_client
        self._url_segment = 'modalities'


    def find_worklist(self, modality: str, query = {}):
        r = self._api_client.post(
            relative_url=f"{self._url_segment}/{modality}/find-worklist",
            json=query
        )

        if r.status_code == 200:
            return r.json()

    def store(self, modality: str, resources_ids: Union[List[str], str], synchronous: bool = True):
        """alias for send"""
        return self.send(modality=modality, resources_ids=resources_ids, synchronous=synchronous)

    def send(self, modality: str, resources_ids: Union[List[str], str], synchronous: bool = True):
        """sends a list of resources to a remote DICOM modality

        Returns
        -------
        Nothing, will raise if failing
        """

        if isinstance(resources_ids, str):
            resources_ids = [resources_ids]

        r = self._api_client.post(
            relative_url=f"{self._url_segment}/{modality}/store",
            json={
                "Resources": resources_ids,
                "Synchronous": synchronous
            })

        return None
