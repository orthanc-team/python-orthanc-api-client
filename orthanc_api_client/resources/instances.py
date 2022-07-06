
from .resources import Resources
from ..tags import Tags
from typing import Union, List, Optional, Any


class Instances(Resources):

    def __init__(self, api_client: 'OrthancApiClient'):
        super().__init__(api_client=api_client, url_segment='instances')

    def get_file(self, orthanc_id: str) -> bytes:
        return self._api_client.get_binary(f"{self._url_segment}/{orthanc_id}/file")

    def get_parent_series_id(self, orthanc_id: str) -> str:
        instance = self._api_client.get_json(f"{self._url_segment}/{orthanc_id}")
        return instance['ParentSeries']

    def get_parent_study_id(self, orthanc_id: str) -> str:
        return self._api_client.series.get_parent_study_id(
            orthanc_id=self.get_parent_series_id(orthanc_id)
        )

    def get_tags(self, orthanc_id: str) -> Tags:
        json_tags = self._api_client.get_json(f"{self._url_segment}/{orthanc_id}/tags")
        return Tags(json_tags)

    def modify_bulk(self, orthanc_ids: List[str] = [], replace_tags: Any = {}, remove_tags: List[str] = [], delete_original: bool = True, force: bool = False) -> List[str]:
        modified_instances_ids = []

        for orthanc_id in orthanc_ids:
            modified_dicom = self.modify(
                orthanc_id=orthanc_id,
                replace_tags=replace_tags,
                remove_tags=remove_tags,
                force=force
            )

            modified_instance_id = self._api_client.upload(modified_dicom)[0]
            if delete_original and modified_instance_id != orthanc_id:
                self.delete(orthanc_id)

            modified_instances_ids.append(modified_instance_id)

        return modified_instances_ids

    def modify(self, orthanc_id: str, replace_tags: Any = {}, remove_tags: List[str] = [], force: bool = False) -> bytes:

        query = {
            "Force": force
        }

        if replace_tags is not None and len(replace_tags) > 0:
            query['Replace'] = replace_tags

        if remove_tags is not None and len(remove_tags) > 0:
            query['Remove'] = remove_tags

        r = self._api_client.post(
            endpoint=f"instances/{orthanc_id}/modify",
            json=query)

        if r.status_code == 200:
            return r.content

        return None  # TODO: raise ?

    def lookup(self, dicom_id: str) -> str:
        """
        finds an instance in Orthanc based on its SOPInstanceUID

        Returns
        -------
        the instance id of the instance or None if not found
        """
        return self._lookup(filter='Instance', dicom_id=dicom_id)

