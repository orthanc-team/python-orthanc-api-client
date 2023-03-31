from .tags import SimplifiedTags
from typing import List, Optional


class SeriesInfo:

    def __init__(self, json_series: object):
        self.main_dicom_tags = SimplifiedTags(json_series.get('MainDicomTags'))
        self.orthanc_id = json_series.get('ID')
        self.dicom_id = self.main_dicom_tags.get('SeriesInstanceUID')
        self.instances_orthanc_ids = json_series.get('Instances')
        self.study_orthanc_id = json_series.get('ParentStudy')


class SeriesStatistics:

    def __init__(self, json_series_stats):
        self.instances_count = int(json_series_stats['CountInstances'])
        self.disk_size = int(json_series_stats['DiskSize'])                  # this is the total size used on disk by the series and all its attachments
        self.uncompressed_size = int(json_series_stats['UncompressedSize'])  # this is the total size of the series and all its attachments once uncompressed


class Series:


    def __init__(self, api_client: 'OrthancApiClient', orthanc_id: str):
        self._api_client = api_client
        self.orthanc_id = orthanc_id
        self._info: SeriesInfo = None
        self._statistics: SeriesStatistics = None
        self._instances: Optional[List['Instances']] = None
        self._study: Optional['Study'] = None

    @staticmethod
    def from_json(api_client, json_series: object):
        series = Series(api_client, json_series.get('ID'))
        series._info = SeriesInfo(json_series)
        return series

    @property
    def info(self):  # lazy loading of main dicom tags ....
        if self._info is None:
            json_series = self._api_client.series.get_json(self.orthanc_id)
            self._info = SeriesInfo(json_series)
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
            json_series_stats = self._api_client.series.get_json_statistics(self.orthanc_id)
            self._statistics = SeriesStatistics(json_series_stats)
        return self._statistics

    @property
    def study(self) -> 'Study':  # lazy creation of study object
        if self._study is None:
            self._study = self._api_client.studies.get(orthanc_id=self.info.study_orthanc_id)
        return self._study

    @property
    def instances(self) -> List['Instance']:  # lazy creation of instances objects
        if self._instances is None:
            self._instances = []
            for instance_id in self.info.instances_orthanc_ids:
                instance = self._api_client.instances.get(orthanc_id=instance_id)
                self._instances.append(instance)

        return self._instances
