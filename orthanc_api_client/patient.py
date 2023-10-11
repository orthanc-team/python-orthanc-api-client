from .tags import SimplifiedTags
from typing import List, Optional
import datetime
from .helpers import from_orthanc_datetime

class PatientInfo:

    def __init__(self, json_patient: object):
        self.main_dicom_tags = SimplifiedTags(json_patient.get('MainDicomTags'))
        self.orthanc_id = json_patient.get('ID')
        self.dicom_id = self.main_dicom_tags.get('PatientID')
        self.studies_ids = json_patient.get('Studies')
        self.last_update = json_patient.get('LastUpdate')

class PatientStatistics:

    def __init__(self, json_patient_stats):
        self.instances_count = int(json_patient_stats['CountInstances'])
        self.series_count = int(json_patient_stats['CountSeries'])
        self.studies_count = int(json_patient_stats['CountStudies'])
        self.disk_size = int(json_patient_stats['DiskSize'])
        self.uncompressed_size = int(json_patient_stats['UncompressedSize'])


class Patient:

    def __init__(self, api_client: 'OrthancApiClient', orthanc_id: str):
        self._api_client = api_client
        self.orthanc_id = orthanc_id
        self._info: PatientInfo = None
        self._statistics: PatientStatistics = None
        self._studies: Optional[List['Study']] = None

    @staticmethod
    def from_json(api_client, json_patient: object):
        patient = Patient(api_client, json_patient.get('ID'))
        patient._info = PatientInfo(json_patient)
        return patient

    @property
    def info(self):  # lazy loading of main dicom tags ....
        if self._info is None:
            json_patient = self._api_client.patients.get_json(self.orthanc_id)
            self._info = PatientInfo(json_patient)
        return self._info

    @property
    def main_dicom_tags(self):
        return self.info.main_dicom_tags

    @property
    def dicom_id(self):
        return self.info.dicom_id

    @property
    def statistics(self):  # lazy loading of statistics ....
        if self._statistics is None:
            json_patient_stats = self._api_client.patients.get_json_statistics(self.orthanc_id)
            self._statistics = PatientStatistics(json_patient_stats)
        return self._statistics

    @property
    def studies(self):  # lazy creation of series objects
        if self._studies is None:
            self._studies = []
            for id in self.info.studies_ids:
                s = self._api_client.studies.get(id)
                self._studies.append(s)

        return self._series

    @property
    def last_update(self):
        return from_orthanc_datetime(self.info.last_update)