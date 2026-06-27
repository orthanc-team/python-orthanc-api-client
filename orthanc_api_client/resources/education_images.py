import json
import typing
from enum import StrEnum
from typing import Dict, List
import uuid
from .resources import Resources
from ..education_image import Image

class Dicomizationtatus(StrEnum):

    RUNNING = 'running'
    SUCCESS = 'success'
    FAILURE = 'failure'

class Images(Resources):

    def __init__(self, api_client: 'OrthancApiClient'):
        super().__init__(api_client=api_client, url_segment='/education/api')

    def get(self, resource_id) -> Image:
        payload = {
            "resource_id": resource_id,
            "project": "_all-studies"
        }
        r = self._api_client.post(
            endpoint=f"{self._url_segment}/list-images",
            json=payload
        )
        print(r.content)
        return Image.from_json(json.loads(r.content))

    def get_images_by_project(self, project_id: str) -> typing.List[Image]:
        payload = {
            "project": project_id
        }
        r = self._api_client.post(
            endpoint=f"{self._url_segment}/list-images",
            json=payload
        )
        return [Image.from_json(img_json) for img_json in json.loads(r.content)]

    def get_series_without_a_project(self) -> typing.List[Image]:
        return self.get_images_by_project(project_id="_unused-series")

    def get_studies_without_a_project(self) -> typing.List[Image]:
        return self.get_images_by_project(project_id="_unused-studies")

    def get_all_images(self) -> typing.List[Image]:
        return self.get_images_by_project(project_id="_all-studies")

    def delete(self, resource_id):
        if self._api_client.studies.get(resource_id) is not None:
            self._api_client.studies.delete(resource_id)
        elif self._api_client.series.get(resource_id) is not None:
            self._api_client.series.delete(resource_id)

    def delete_all(self):
        self._api_client.delete_all_content()

    def link_image_to_project(self, resource_id: str, project_id: str, resource_level: str="Series"):
        """
        resource_level: 'Study' or 'Series'
        """
        payload = {
            'resource' : {
                'resource-id' : resource_id,
                'level' : resource_level
            },
            'project' : project_id,
        }
        r = self._api_client.post(
            endpoint=f"{self._url_segment}/link",
            json=payload
        )
        r.raise_for_status()


    def upload_and_dicomize(self, file_path: str, description: str) -> str:

        # first: upload
        upload_id = str(uuid.uuid4())

        chunk_size = 1024 * 1024  # 1 MB

        with open(file_path, "rb") as f:
            f.seek(0, 2)
            file_size = f.tell()
            f.seek(0)

            start = 0

            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break

                end = start + len(chunk)

                headers = {
                    "Content-Range": f"bytes {start}-{end - 1}/{file_size}",
                    "Upload-Id": upload_id,
                    "Content-Type": "application/octet-stream",
                }
                response = self._api_client.post(
                    endpoint=f"{self._url_segment}/upload",
                    data=chunk,
                    headers=headers
                )

                response.raise_for_status()

                start = end

        # then: dicomize
        payload = {
            "upload-id": upload_id,
            "type": "wsi",
            "background-color": "white",
            "force-openslide": False,
            "reconstruct-pyramid": True,
            "study-description": description,
        }
        r = self._api_client.post(
            endpoint=f"{self._url_segment}/dicomization",
            json=payload
        )
        r.raise_for_status()

        return upload_id

    def get_dicomization_status(self, upload_id) -> str:
        r = self._api_client.get(f"{self._url_segment}/dicomization")

        r.raise_for_status()

        for job in json.loads(r.content):
            #print(job['upload-id'])
            if job['upload-id'] == upload_id:
                return job['status']
        # TODO: raise exception?
        return None

    def change_title(self, resource_id: str, title: str, level: str="Series") -> str:
        payload = {
            'resource' : {
                'resource-id' : resource_id,
                'level' : level,
            },
            "title": title
        }

        r = self._api_client.post(
            endpoint=f"{self._url_segment}/change-title",
            json=payload
        )
        r.raise_for_status()