import os

from .resources import Resources
from ..tags import Tags
from typing import Union, List, Optional, Any
from ..downloaded_instance import DownloadedInstance
from ..instance import InstanceInfo, Instance


class Instances(Resources):

    def __init__(self, api_client: 'OrthancApiClient'):
        super().__init__(api_client=api_client, url_segment='instances')

    def get(self, orthanc_id: str) -> Instance:
        return Instance(api_client=self._api_client, orthanc_id=orthanc_id)

    def get_file(self, orthanc_id: str) -> bytes:
        return self._api_client.get_binary(f"{self._url_segment}/{orthanc_id}/file")

    def get_parent_series_id(self, orthanc_id: str) -> str:
        return self._api_client.get_json(f"{self._url_segment}/{orthanc_id}/series")['ID']

    def get_parent_study_id(self, orthanc_id: str) -> str:
        return self._api_client.get_json(f"{self._url_segment}/{orthanc_id}/study")['ID']

    def get_parent_patient_id(self, orthanc_id: str) -> str:
        return self._api_client.get_json(f"{self._url_segment}/{orthanc_id}/patient")['ID']

    def get_tags(self, orthanc_id: str) -> Tags:
        json_tags = self._api_client.get_json(f"{self._url_segment}/{orthanc_id}/tags")
        return Tags(json_tags)


    def modify(self, orthanc_id: str, replace_tags: Any = {}, remove_tags: List[str] = [], keep_tags: List[str] = [], force: bool = False) -> bytes:

        query = {
            "Force": force
        }

        if replace_tags is not None and len(replace_tags) > 0:
            query['Replace'] = replace_tags

        if remove_tags is not None and len(remove_tags) > 0:
            query['Remove'] = remove_tags

        if keep_tags is not None and len(keep_tags) > 0:
            query['Keep'] = keep_tags

        r = self._api_client.post(
            endpoint=f"instances/{orthanc_id}/modify",
            json=query)

        if r.status_code == 200:
            return r.content

        return None  # TODO: raise ?

    def lookup(self, dicom_id: str) -> str:
        """
        finds an instance in Orthanc based on its SOPInstanceUID

        Returns
        -------
        the instance id of the instance or None if not found
        """
        return self._lookup(filter='Instance', dicom_id=dicom_id)

    def is_pdf(self, instance_id: str):
        """
        checks if the instance contains a pdf
        Args:
            instance_id: The id of the instance to check

        Returns: True if the instance contain a pdf, False ortherwise
        """
        tags = self.get_tags(instance_id)
        mime_type = tags.get('MIMETypeOfEncapsulatedDocument')
        return mime_type == 'application/pdf'

    def download_pdf(self, instance_id: str, path: str):
        """
        downloads the pdf from the instance (if the instance does contain a PDF !)
        Args:
            instance_id: The id of the instance
            path: the path where to save the PDF file

        Returns:
            the path where the PDF has been saved (same as input argument)
        """

        response = self._api_client.get(
            endpoint = f"instances/{instance_id}/pdf")
        with open(path, 'wb') as f:
            f.write(response.content)

        return path

    def download_instance(self, instance_id: str, path: str) -> DownloadedInstance:
        """
        downloads the instance DICOM file to disk
        Args:
            instance_id: the instance id to download
            path: the file path where to store the downloaded file

        Returns:
            a DownloadedInstance object with the instanceId and the path
        """
        file_content = self.get_file(instance_id)
        with open(path, 'wb') as f:
            f.write(file_content)

        return DownloadedInstance(instance_id, path)

    def download_instances(self, instances_ids: List[str], path: str) -> List[DownloadedInstance]:
        """
        downloads the instances DICOM files to disk
        Args:
            instances_ids: the instances ids to download
            path: the folder path where to store the downloaded files

        Returns:
            a list of DownloadedInstance objects with the instanceId and the path
        """
        downloaded_instances = []
        for instance_id in instances_ids:
            downloaded_instances.append(self.download_instance(instance_id = instance_id,
                                                               path = os.path.join(path, instance_id + ".dcm")))

        return downloaded_instances
