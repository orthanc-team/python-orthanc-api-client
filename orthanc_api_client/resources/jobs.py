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
