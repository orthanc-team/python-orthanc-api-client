import json
import typing
from typing import Dict

from .resources import Resources
from ..education_projet import Project
#from orthanc_api_client import OrthancApiClient


class Projects(Resources):

    def __init__(self, api_client: 'OrthancApiClient'):
        super().__init__(api_client=api_client, url_segment='/education/api/projects')

    def create(self, name: str, description: str) :
        payload = {
            "name": name,
            "description": description
        }

        r = self._api_client.post(
            endpoint=f"{self._url_segment}/",
            json=payload
        )
        r.raise_for_status()

        return r.json()['id']

    def delete(self, project_id: str):
        self._api_client.delete(f"{self._url_segment}/{project_id}")


    def delete_all(self):
        prjs = self.get_all()
        for prj in prjs:
            self.delete(prj.id)

    def get(self, project_id: str) -> Project:
        r = self._api_client.get(f"{self._url_segment}/{project_id}")
        r.raise_for_status()

        return Project.from_json(self._api_client, json.loads(r.content))

    def get_all(self) -> typing.List[Project]:
        r = self._api_client.get(f"{self._url_segment}/")
        r.raise_for_status()

        return [Project.from_json(self._api_client, prj_json) for prj_json in json.loads(r.content)]

    def set_viewer(self, project_id: str, viewer: str):
        if viewer not in [ 'stone', 'volview', 'wsi', 'ohif-basic', 'ohif-volume', 'ohif-tumor', 'ohif-segmentation' ]:
            raise Exception(f'viewer {viewer} not supported')

        r=self._api_client.put(f"{self._url_segment}/{project_id}/primary-viewer", data=json.dumps(viewer))
        r.raise_for_status()