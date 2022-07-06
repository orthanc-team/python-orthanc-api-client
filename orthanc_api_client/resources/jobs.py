from .resources import Resources
from ..tags import Tags
from typing import List, Any
from ..exceptions import *
from ..job import Job


class Jobs(Resources):

    def __init__(self, api_client: 'OrthancApiClient'):
        super().__init__(api_client=api_client, url_segment='jobs')

    def get(self, orthanc_id: str) -> Job:
        return Job(api_client=self._api_client, orthanc_id=orthanc_id)

    def _post_job_action(self, orthanc_id: str, action: str):
        self._api_client.post(
            endpoint=f"{self._url_segment}/{orthanc_id}/{action}",
            data="")

    def retry(self, orthanc_id: str):
        self._post_job_action(orthanc_id=orthanc_id, action='resubmit')

    def resubmit(self, orthanc_id: str):
        self._post_job_action(orthanc_id=orthanc_id, action='resubmit')

    def cancel(self, orthanc_id: str):
        self._post_job_action(orthanc_id=orthanc_id, action='cancel')

    def pause(self, orthanc_id: str):
        self._post_job_action(orthanc_id=orthanc_id, action='pause')

    def resume(self, orthanc_id: str):
        self._post_job_action(orthanc_id=orthanc_id, action='resume')
