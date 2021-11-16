
from .resources import Resources
from .http_client import HttpClient


class Instances(Resources):

    def __init__(self, http_client: HttpClient):
        super().__init__(http_client=http_client, url_segment='instances')

    def get_file(self, instance_id: str):
        return self._http_client.get_binary(f"/{self._url_segment}/{instance_id}/file")