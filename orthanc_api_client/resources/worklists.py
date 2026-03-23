import json
import typing
from typing import Dict

from .resources import Resources
from ..tags import Tags

class Worklists(Resources):

    def __init__(self, api_client: 'OrthancApiClient'):
        super().__init__(api_client=api_client, url_segment='worklists')

    def create(self, values: typing.Dict[str, str]):
        payload = {
            "Tags": values
        }

        r = self._api_client.post(
            endpoint=f"{self._url_segment}/create",
            json=payload
        )
        return r.json()['ID']

    def get(self, orthanc_id: str) -> Dict:
        r = self._api_client.get(f"{self._url_segment}/{orthanc_id}")
        return json.loads(r.content)

    def get_all(self) -> typing.List[Dict]:
        r = self._api_client.get(f"{self._url_segment}/")
        return json.loads(r.content)

    def get_all_ids(self) -> typing.List[str]:
        wl_list = self.get_all()

        return [x["ID"] for x in wl_list]

    def get_tags(self, orthanc_id: str) -> Tags:
        wl = self.get(orthanc_id)
        return Tags(wl.get("Tags"))

