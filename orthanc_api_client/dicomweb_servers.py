from typing import List, Union

from .resources import Resources
from .exceptions import *


class DicomWebServers(Resources):

    def __init__(self, api_client: 'OrthancApiClient'):
        super().__init__(api_client=api_client, url_segment='dicom-web/servers')


    def send(self, target_server: str, resources_ids: Union[List[str], str], synchronous: bool = True):
        """sends a list of resources to a remote DicomWeb server

        Returns
        -------
        Nothing, will raise if failing 
        """

        if isinstance(resources_ids, str):
            resources_ids = [resources_ids]

        r = self._api_client.post(
            relative_url=f"{self._url_segment}/{target_server}/stow",
            json={
                "Resources" : resources_ids,
                "Synchronous" : synchronous
            })

        return None
