from .tags import SimplifiedTags
from typing import List, Optional
import datetime
from .helpers import from_orthanc_datetime

class StudyInfo:

    def __init__(self, json_study: object):
        self.main_dicom_tags = SimplifiedTags(json_study.get('MainDicomTags'))
        self.patient_main_dicom_tags = SimplifiedTags(json_study.get('PatientMainDicomTags'))
        self.orthanc_id = json_study.get('ID')
        self.dicom_id = self.main_dicom_tags.get('StudyInstanceUID')
        self.series_ids = json_study.get('Series')
        self.patient_orthanc_id = json_study.get('ParentPatient')
        self.last_update = json_study.get('LastUpdate')


class StudyStatistics:

    def __init__(self, json_study_stats):
        self.instances_count = int(json_study_stats['CountInstances'])
        self.series_count = int(json_study_stats['CountSeries'])
        self.disk_size = int(json_study_stats['DiskSize'])                  # this is the total size used on disk by the study and all its attachments
        self.uncompressed_size = int(json_study_stats['UncompressedSize'])  # this is the total size of the study and all its attachments once uncompressed


class Study:

    def __init__(self, api_client: 'OrthancApiClient', orthanc_id: str):
        self._api_client = api_client
        self.orthanc_id = orthanc_id
        self._info: StudyInfo = None
        self._statistics: StudyStatistics = None
        self._series: Optional[List['Series']] = None

    @staticmethod
    def from_json(api_client, json_study: object):
        study = Study(api_client, json_study.get('ID'))
        study._info = StudyInfo(json_study)
        return study

    @property
    def info(self):  # lazy loading of main dicom tags ....
        if self._info is None:
            json_study = self._api_client.studies.get_json(self.orthanc_id)
            self._info = StudyInfo(json_study)
        return self._info

    @property
    def main_dicom_tags(self):
        return self.info.main_dicom_tags

    @property
    def patient_main_dicom_tags(self):
        return self.info.patient_main_dicom_tags

    @property
    def dicom_id(self):
        return self.info.dicom_id

    @property
    def statistics(self):  # lazy loading of statistics ....
        if self._statistics is None:
            json_study_stats = self._api_client.studies.get_json_statistics(self.orthanc_id)
            self._statistics = StudyStatistics(json_study_stats)
        return self._statistics

    @property
    def series(self):  # lazy creation of series objects
        if self._series is None:
            self._series = []
            for id in self.info.series_ids:
                s = self._api_client.series.get(id)
                self._series.append(s)

        return self._series

    @property
    def last_update(self):
        return from_orthanc_datetime(self.info.last_update)