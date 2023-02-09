from .tags import SimplifiedTags
from typing import List, Optional


class InstanceInfo:

    def __init__(self, json_instance: object):
        self.main_dicom_tags = SimplifiedTags(json_instance.get('MainDicomTags'))
        self.orthanc_id = json_instance.get('ID')
        self.dicom_id = self.main_dicom_tags.get('SOPInstanceUID')
        self.series_orthanc_id = json_instance.get('ParentSeries')


class Instance:


    def __init__(self, api_client: 'OrthancApiClient', orthanc_id: str):
        self._api_client = api_client
        self.orthanc_id = orthanc_id
        self._info: Optional[InstanceInfo] = None
        self._series: Optional['Series'] = None
        self._tags: Optional[SimplifiedTags] = None

    @staticmethod
    def from_json(api_client, json_instance: object):
        instance = Instance(api_client, json_instance.get('ID'))
        instance._info = InstanceInfo(json_instance)
        return instance

    @property
    def info(self):  # lazy loading of main dicom tags ....
        if self._info is None:
            self._load_info()
        return self._info

    @property
    def dicom_id(self):
        return self.info.dicom_id

    def _load_info(self):
        json_instance = self._api_client.instances.get_json(self.orthanc_id)
        self._info = InstanceInfo(json_instance)

    @property
    def series(self) -> 'Series':  # lazy creation of series object
        if self._series is None:
            self._series = self._api_client.series.get(orthanc_id=self.info.series_orthanc_id)
        return self._series

    @property
    def tags(self):  # lazy loading of tags ....
        if self._tags is None:
            self._tags = self._api_client.instances.get_tags(orthanc_id=self.orthanc_id)
        return self._tags
