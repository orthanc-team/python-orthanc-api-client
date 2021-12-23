
from .resources import Resources


class Instances(Resources):

    def __init__(self, api_client: 'OrthancApiClient'):
        super().__init__(api_client=api_client, url_segment='instances')

    def get_file(self, orthanc_id: str) -> bytes:
        return self._api_client.get_binary(f"/{self._url_segment}/{orthanc_id}/file")

    def get_parent_series_id(self, orthanc_id: str) -> str:
        instance = self._api_client.get_json(f"/{self._url_segment}/{orthanc_id}")
        return instance['ParentSeries']

    def get_parent_study_id(self, orthanc_id: str) -> str:
        return self._api_client.series.get_parent_study_id(
            orthanc_id=self.get_parent_series_id(orthanc_id)
        )
