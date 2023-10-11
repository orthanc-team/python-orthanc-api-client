import datetime
from typing import List, Any, Union, Set

from .resources import Resources
from ..tags import Tags
from ..exceptions import *
from ..patient import PatientInfo, Patient
from ..helpers import to_dicom_date, to_dicom_time
from ..downloaded_instance import DownloadedInstance
from ..labels_constraint import LabelsConstraint

class Patients(Resources):

    def __init__(self, api_client: 'OrthancApiClient'):
        super().__init__(api_client=api_client, url_segment='patients')

    def get(self, orthanc_id: str) -> Patient:
        return Patient(api_client=self._api_client, orthanc_id=orthanc_id)

    def get_instances_ids(self, orthanc_id: str) -> List[str]:
        instances_ids = []
        patient_info = self._api_client.get_json(f"{self._url_segment}/{orthanc_id}")
        for study_id in patient_info["Studies"]:
            instances_ids.extend(self._api_client.studies.get_instances_ids(study_id))

        return instances_ids

    def get_series_ids(self, orthanc_id: str) -> List[str]:
        series_ids = []
        patient_info = self._api_client.get_json(f"{self._url_segment}/{orthanc_id}")
        for study_id in patient_info["Studies"]:
            series_ids.extend(self._api_client.studies.get_series_ids(study_id))

        return series_ids

    def get_studies_ids(self, orthanc_id: str) -> List[str]:
        patient_info = self._api_client.get_json(f"{self._url_segment}/{orthanc_id}")
        return patient_info["Studies"]

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

    def lookup(self, dicom_id: str) -> str:
        """
        finds a patient in Orthanc based on its PatientID

        Returns
        -------
        the patient id of the patient or None if not found
        """
        return self._lookup(filter='Patient', dicom_id=dicom_id)

    def find(self, query: object, case_sensitive: bool = True, labels: [str] = [], labels_constraint: LabelsConstraint = LabelsConstraint.ANY) -> List[Patient]:
        """
        find a patient in Orthanc based on the query and the labels

        args:
            labels: the list of the labels to filter to
            labels_constraint: "Any" (=default value), "All", "None"
        """
        payload = {
            "Level": "Patient",
            "Query": query,
            "Expand": True,
            "CaseSensitive": case_sensitive,
            "Labels": labels,
            "LabelsConstraint": labels_constraint
        }

        r = self._api_client.post(
            endpoint=f"tools/find",
            json=payload)

        patients = []
        for json_patient in r.json():
            patients.append(Patient.from_json(self._api_client, json_patient))

        return patients

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

        return self._api_client.instances.get_parent_patient_id(modified_instances_ids[0])

    def get_tags(self, orthanc_id: str) -> Tags:
        """
        returns tags from a "random" instance in which you should safely get the patient tags
        """
        return self._api_client.instances.get_tags(self.get_first_instance_id(orthanc_id=orthanc_id))

    def download_instances(self, patient_id: str, path: str) -> List['DownloadedInstance']:
        """
        downloads all instances from the patient to disk
        Args:
            patient_id: the patientid to download
            path: the directory path where to store the downloaded files

        Returns:
            an array of DownloadedInstance
        """
        return self._api_client.instances.download_instances(self.get_instances_ids(patient_id), path)
