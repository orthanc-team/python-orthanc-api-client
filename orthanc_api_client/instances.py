
from .resources import Resources


class Instances(Resources):

    def __init__(self, api_client: 'OrthancApiClient'):
        super().__init__(api_client=api_client, url_segment='instances')

    def get_file(self, instance_id: str):
        return self._api_client.get_binary(f"/{self._url_segment}/{instance_id}/file")