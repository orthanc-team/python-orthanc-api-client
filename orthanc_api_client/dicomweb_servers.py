from typing import List, Union

from .exceptions import *
from .job import Job


class DicomWebServers:

    def __init__(self, api_client: 'OrthancApiClient'):
        self._api_client = api_client
        self._url_segment = 'dicom-web/servers'

    def send_async(self, target_server: str, resources_ids: Union[List[str], str]) -> Job:
        """sends a list of resources to a remote DicomWeb server

        Returns
        -------
        The job that has been created
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

    def send(self, target_server: str, resources_ids: Union[List[str], str]):
        """sends a list of resources to a remote DicomWeb server
        """

        if isinstance(resources_ids, str):
            resources_ids = [resources_ids]

        self._api_client.post(
            endpoint=f"{self._url_segment}/{target_server}/stow",
            json={
                "Resources": resources_ids,
                "Synchronous": True
            })

    def retrieve_instance(self, remote_server: str, study_instance_uid: str, series_instance_uid: str, sop_instance_uid: str) -> bool:
        """retrieves a list of series from a remote DicomWeb server
        Returns true if received.
        """
        return self.retrieve_resources(remote_server=remote_server, resources=[{
            'Study': study_instance_uid,
            'Series': series_instance_uid,
            'Instance': sop_instance_uid
        }]) == 1

    def retrieve_series(self, remote_server: str, study_instance_uid: str, series_instance_uid: str) -> int:
        """retrieves a list of series from a remote DicomWeb server
        Returns the number of instances received.
        """
        return self.retrieve_resources(remote_server=remote_server, resources=[{
            'Study': study_instance_uid,
            'Series': series_instance_uid
        }])

    def retrieve_study(self, remote_server: str, study_instance_uid: str) -> int:
        """retrieves a study from a remote DicomWeb server
        Returns the number of instances received.
        """
        return self.retrieve_resources(remote_server=remote_server, resources=[{
            'Study': study_instance_uid
        }])
    
    def retrieve_resources(self, remote_server: str, resources: List[object]) -> int:
        """Retrieves a list of resources from a remote DicomWeb server.
        Returns the number of instances received.
        """

        r = self._api_client.post(
            endpoint=f"{self._url_segment}/{remote_server}/retrieve",
            json={
                "Resources": resources,
                "Synchronous": True
            })
        
        return int(r.json()['ReceivedInstancesCount'])