
from .resources import Resources


class Instances(Resources):

    def __init__(self, api_client: 'OrthancApiClient'):
        super().__init__(api_client=api_client, url_segment='instances')

    def get_file(self, instance_id: str) -> bytes:
        return self._api_client.get_binary(f"/{self._url_segment}/{instance_id}/file")

    def get_parent_series_id(self, instance_id: str) -> str:
        instance = self._api_client.get_json(f"/{self._url_segment}/{instance_id}")
        return instance['ParentSeries']

    def get_parent_study_id(self, instance_id: str) -> str:
        return self._api_client.series.get_parent_study_id(
            series_id=self.get_parent_series_id(instance_id)
        )
