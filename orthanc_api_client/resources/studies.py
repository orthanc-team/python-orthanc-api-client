import typing

from .resources import Resources
from ..tags import Tags
from ..exceptions import *
from ..study import StudyInfo, Study
from typing import List, Any


class Studies(Resources):

    def __init__(self, api_client: 'OrthancApiClient'):
        super().__init__(api_client=api_client, url_segment='studies')

    def get(self, orthanc_id: str) -> Study:
        return Study(api_client=self._api_client, orthanc_id=orthanc_id)

    def get_instances_ids(self, orthanc_id: str) -> List[str]:
        instances_ids = []
        study_info = self._api_client.get_json(f"{self._url_segment}/{orthanc_id}")
        for series_id in study_info["Series"]:
            instances_ids.extend(self._api_client.series.get_instances_ids(series_id))

        return instances_ids

    def get_first_instance_id(self, orthanc_id: str) -> str:
        return self.get_instances_ids(orthanc_id=orthanc_id)[0]

    def lookup(self, dicom_id: str) -> str:
        """
        finds a study in Orthanc based on its StudyInstanceUid

        Returns
        -------
        the instance id of the study or None if not found
        """
        study_ids = self._api_client.lookup(needle=dicom_id, filter='Study')
        if len(study_ids) == 1:
            return study_ids[0]

        if len(study_ids) > 1:
            raise TooManyResourcesFound()        
        return None

    def find(self, query: object, case_sensitive: bool = True) -> typing.List[Study]:
        payload = {
            "Level": "Study",
            "Query": query,
            "Expand": True,
            "CaseSensitive": case_sensitive
        }

        r = self._api_client.post(
            relative_url=f"/tools/find",
            json=payload)

        studies = []
        for json_study in r.json():
            studies.append(Study.from_json(self._api_client, json_study))

        return studies

    def anonymize(self, orthanc_id: str, replace_tags={}, keep_tags=[], delete_original=True, force=False) -> str:
        return self._anonymize(
            orthanc_id=orthanc_id,
            replace_tags=replace_tags,
            keep_tags=keep_tags,
            delete_original=delete_original,
            force=force
        )

    def modify(self, orthanc_id: str, replace_tags={}, remove_tags=[], delete_original=True, force=False) -> str:
        return self._modify(
            orthanc_id=orthanc_id,
            replace_tags=replace_tags,
            remove_tags=remove_tags,
            delete_original=delete_original,
            force=force
        )

    def modify_instance_by_instance(self, orthanc_id: str, replace_tags: Any = {}, remove_tags: List[str] = [], delete_original: bool = True, force: bool = True) -> str:
        modified_instances_ids = self._api_client.instances.modify_bulk(
            orthanc_ids=self.get_instances_ids(orthanc_id),
            replace_tags=replace_tags,
            remove_tags=remove_tags,
            delete_original=delete_original,
            force=force
        )

        return self._api_client.instances.get_parent_study_id(modified_instances_ids[0])

    def get_tags(self, orthanc_id: str) -> Tags:
        """
        returns tags from a "random" instance in which you should safely get the study/patient tags
        """
        return self._api_client.instances.get_tags(self.get_first_instance_id(orthanc_id=orthanc_id))
