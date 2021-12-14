from .resources import Resources
from .exceptions import *


class Series(Resources):

    def __init__(self, api_client: 'OrthancApiClient'):
        super().__init__(api_client=api_client, url_segment='series')

    def get_parent_study_id(self, series_id: str) -> str:
        series = self._api_client.get_json(f"/{self._url_segment}/{series_id}")
        return series['ParentStudy']
