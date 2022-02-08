from typing import List, Union

from .exceptions import *


class DicomModalities:

    def __init__(self, api_client: 'OrthancApiClient'):
        self._api_client = api_client
        self._url_segment = 'modalities'


    def find_worklist(self, modality: str, query = {}):
        r = self._api_client.post(
            relative_url=f"{self._url_segment}/{modality}/find-worklist",
            json=query
        )

        if r.status_code == 200:
            return r.json()