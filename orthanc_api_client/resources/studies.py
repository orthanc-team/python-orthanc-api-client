import datetime
from typing import List, Any, Union, Set

from .resources import Resources
from ..tags import Tags
from ..exceptions import *
from ..study import StudyInfo, Study
from ..helpers import to_dicom_date, to_dicom_time
from ..downloaded_instance import DownloadedInstance
from ..labels_constraint import LabelsConstraint

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

    def get_series_ids(self, orthanc_id: str) -> List[str]:
        study_info = self._api_client.get_json(f"{self._url_segment}/{orthanc_id}")
        return study_info["Series"]

    def get_first_instance_id(self, orthanc_id: str) -> str:
        return self.get_instances_ids(orthanc_id=orthanc_id)[0]

    def get_first_instance_tags(self, orthanc_id: str) -> Tags:
        return self._api_client.instances.get_tags(self.get_first_instance_id(orthanc_id))

    """gets the list of modalities from all series"""
    def get_modalities(self, orthanc_id: str) -> Set[str]:
        modalities = set()
        for series_id in self.get_series_ids(orthanc_id):
            modalities.add(self._api_client.series.get(series_id).main_dicom_tags.get('Modality'))
        return modalities

    def get_parent_patient_id(self, orthanc_id: str) -> str:
        return self._api_client.get_json(f"{self._url_segment}/{orthanc_id}/patient")['ID']

    def lookup(self, dicom_id: str) -> str:
        """
        finds a study in Orthanc based on its StudyInstanceUid

        Returns
        -------
        the instance id of the study or None if not found
        """
        return self._lookup(filter='Study', dicom_id=dicom_id)

    def find(self, query: object, case_sensitive: bool = True, labels: [str] = [], labels_constraint: LabelsConstraint = LabelsConstraint.ANY) -> List[Study]:
        """
        find a study in Orthanc based on the query and the labels

        args:
            labels: the list of the labels to filter to
            labels_constraint: "Any" (=default value), "All", "None"
        """
        payload = {
            "Level": "Study",
            "Query": query,
            "Expand": True,
            "CaseSensitive": case_sensitive,
            "Labels": labels,
            "LabelsConstraint": labels_constraint
        }

        r = self._api_client.post(
            endpoint=f"tools/find",
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

    def modify(self, orthanc_id: str, replace_tags: Any = {}, remove_tags: List[str] = [], keep_tags: List[str] = [], delete_original=True, force=False) -> str:
        return self._modify(
            orthanc_id=orthanc_id,
            replace_tags=replace_tags,
            remove_tags=remove_tags,
            delete_original=delete_original,
            keep_tags=keep_tags,
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

    def merge(self, target_study_id: str, source_series_id: Union[List[str], str], keep_source: bool):

        if isinstance(source_series_id, str):
            source_series_id = [source_series_id]

        return self._api_client.post(
            endpoint=f"{self._url_segment}/{target_study_id}/merge",
            json={
                "Resources": source_series_id,
                "KeepSource": keep_source
            }
        )

    def attach_pdf(self, study_id: str, pdf_path: str, series_description: str, datetime: datetime.datetime = None) -> str:
        """
        Creates a new instance with the PDF embedded.  This instance is a part of a new series attached to an existing study

        Returns:
            the instance_orthanc_id of the created instance
        """
        series_tags = {}
        series_tags["SeriesDescription"] = series_description
        if datetime is not None:
            series_tags["SeriesDate"] = to_dicom_date(datetime)
            series_tags["SeriesTime"] = to_dicom_time(datetime)

        return self._api_client.create_pdf(pdf_path, series_tags, parent_id = study_id)

    def get_pdf_instances(self, study_id: str, max_instance_count_in_series_to_analyze: int = 2) -> List[str]:
        """
        Returns the instanceIds of the instances containing PDF
        Args:
            study_id: The id of the study to search in
            max_instance_count_in_series_to_analyze: skip series containing too many instances (they are very unlikely to contain pdf reports).  set it to 0 to disable the check.

        Returns: an array of instance orthancId
        """

        pdf_ids = []
        series_list = self.get_series_ids(study_id)

        for series_id in series_list:
            instances_ids = self._api_client.series.get_instances_ids(series_id)
            if max_instance_count_in_series_to_analyze > 0 and len(instances_ids) <= max_instance_count_in_series_to_analyze:
                for instance_id in instances_ids:
                    if self._api_client.instances.is_pdf(instance_id):
                        pdf_ids.append(instance_id)

        return pdf_ids

    def download_instances(self, study_id: str, path: str) -> List['DownloadedInstance']:
        """
        downloads all instances from the study to disk
        Args:
            study_id: the studyid to download
            path: the directory path where to store the downloaded files

        Returns:
            an array of DownloadedInstance
        """
        return self._api_client.instances.download_instances(self.get_instances_ids(study_id), path)
