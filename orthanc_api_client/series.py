from .resources import Resources
from typing import List
from .exceptions import *


class Series(Resources):

    def __init__(self, api_client: 'OrthancApiClient'):
        super().__init__(api_client=api_client, url_segment='series')

    def get_parent_study_id(self, orthanc_id: str) -> str:
        series = self._api_client.get_json(f"/{self._url_segment}/{orthanc_id}")
        return series['ParentStudy']

    def get_ordered_instances_ids(self, orthanc_id: str) -> List[str]:
        ordered_slices = self._api_client.get_json(f"/{self._url_segment}/{orthanc_id}/ordered-slices")
        return [ss[0] for ss in ordered_slices.get('SlicesShort')]

    def get_middle_instance_id(self, orthanc_id: str) -> str:
        ordered_instances_ids = self.get_ordered_instances_ids(orthanc_id=orthanc_id)
        return ordered_instances_ids[int(len(ordered_instances_ids)/2)]

    def get_preview_url(self, orthanc_id: str) -> str:
        middle_instance_id = self.get_middle_instance_id(orthanc_id=orthanc_id)
        return f"/{self._url_segment}/{middle_instance_id}/preview"
