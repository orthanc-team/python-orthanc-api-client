from .tags import SimplifiedTags
import typing


class SeriesInfo:

    def __init__(self, json_series: object):
        self.main_dicom_tags = SimplifiedTags(json_series.get('MainDicomTags'))
        self.orthanc_id = json_series.get('ID')
        self.dicom_id = self.main_dicom_tags.get('SeriesInstanceUID')
        self.instances_orthanc_ids = json_series.get('Instances')
        self.study_orthanc_id = json_series.get('ParentStudy')


class Series:

    def __init__(self, api_client, orthanc_id):
        self._api_client = api_client
        self.orthanc_id = orthanc_id
        self._info = None
        self._study = None
        self._instances = None

    @staticmethod
    def from_json(api_client, json_series: object):
        series = Series(api_client, json_series.get('ID'))
        series._info = SeriesInfo(json_series)
        return series

    @property
    def info(self):  # lazy loading of main dicom tags ....
        if self._info is None:
            self._load_info()
        return self._info

    @property
    def main_dicom_tags(self):
        return self.info.main_dicom_tags

    @property
    def dicom_id(self):
        return self.info.dicom_id

    def _load_info(self):
        json_series = self._api_client.series.get_json(self.orthanc_id)
        self._info = SeriesInfo(json_series)

    @property
    def study(self) -> 'Study':  # lazy creation of study object
        if self._study is None:
            self._study = self._api_client.studies.get(orthanc_id=self.info.study_orthanc_id)
        return self._study

    @property
    def instances(self) -> typing.List['Instance']:  # lazy creation of instances objects
        if self._instances is None:
            self._instances = []
            for instance_id in self.info.instances_orthanc_ids:
                instance = self._api_client.instances.get(orthanc_id=instance_id)
                self._instances.append(instance)

        return self._instances
