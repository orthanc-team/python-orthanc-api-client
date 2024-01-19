from typing import List, Union

from .exceptions import *
from .job import Job
from .change import ResourceType


class RemoteJob:
    def __init__(self, remote_job_id, remote_url):
        self.remote_job_id = remote_job_id
        self.remote_url = remote_url


class Transfers:

    def __init__(self, api_client: 'OrthancApiClient'):
        self._api_client = api_client
        self._url_segment = 'transfers'

    def send_async(self, target_peer: str, resources_ids: Union[List[str], str], resource_type: ResourceType, compress: bool = True) -> Union[Job, RemoteJob]:

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
        if r.status_code == 200 and "RemoteJob" in r.json():
            return RemoteJob(remote_job_id=r.json()["RemoteJob"], remote_url=r.json()["URL"])
        elif r.status_code == 200 and "ID" in r.json():
            return Job(api_client=self._api_client, orthanc_id=r.json()['ID'])
        else:
            raise HttpError(http_status_code=r.status_code, msg="Error while sending through transfers plugin", url=r.url, request_response=r)


    def send(self, target_peer: str, resources_ids: Union[List[str], str], resource_type: ResourceType, compress: bool = True, polling_interval: float = 0.2):

        job = self.send_async(
            target_peer=target_peer,
            resources_ids=resources_ids,
            resource_type=resource_type,
            compress=compress
        )

        if isinstance(job, RemoteJob):
            raise OrthancApiException(msg="Pull jobs are not supported in send(), use send_async()")

        job.wait_completed(polling_interval=polling_interval)
