import os

from .resources import Resources
from ..tags import Tags
from typing import List, Any
from ..downloaded_instance import DownloadedInstance
from ..series import SeriesInfo, Series


class SeriesList(Resources):

    def __init__(self, api_client: 'OrthancApiClient'):
        super().__init__(api_client=api_client, url_segment='series')

    def get(self, orthanc_id: str) -> Series:
        return Series(api_client=self._api_client, orthanc_id=orthanc_id)

    def get_instances_ids(self, orthanc_id: str) -> List[str]:
        return self._api_client.get_json(f"{self._url_segment}/{orthanc_id}")["Instances"]

    def get_first_instance_id(self, orthanc_id: str) -> str:
        return self.get_instances_ids(orthanc_id=orthanc_id)[0]

    def get_parent_study_id(self, orthanc_id: str) -> str:
        return self._api_client.get_json(f"{self._url_segment}/{orthanc_id}/study")['ID']

    def get_parent_patient_id(self, orthanc_id: str) -> str:
        return self._api_client.get_json(f"{self._url_segment}/{orthanc_id}/patient")['ID']

    def get_ordered_instances_ids(self, orthanc_id: str) -> List[str]:
        ordered_slices = self._api_client.get_json(f"{self._url_segment}/{orthanc_id}/ordered-slices")
        return [ss[0] for ss in ordered_slices.get('SlicesShort')]

    def get_middle_instance_id(self, orthanc_id: str) -> str:
        ordered_instances_ids = self.get_ordered_instances_ids(orthanc_id=orthanc_id)
        return ordered_instances_ids[int(len(ordered_instances_ids) / 2)]

    def get_preview_url(self, orthanc_id: str) -> str:
        middle_instance_id = self.get_middle_instance_id(orthanc_id=orthanc_id)
        return f"instances/{middle_instance_id}/preview"

    def get_preview_file(self, orthanc_id: str, jpeg_format: bool = False) -> bytes:
        """
        downloads the preview file (middle instance of the series) in png format (or jpeg)
        Args:
            orthanc_id: the series id to download the preview file from
            jpeg_format: replace default png format by jpeg format

        Returns:
            
        """
        url = self.get_preview_url(orthanc_id=orthanc_id)
        if jpeg_format:
            headers = { "Accept": "image/jpeg"}
        else:
            headers = { "Accept": "image/png"}

        parameters = {"returnUnsupportedImage": True}
        return self._api_client.get_binary(endpoint=url, headers=headers, params=parameters)

    def anonymize(self, orthanc_id: str, replace_tags={}, keep_tags=[], delete_original=True, force=False) -> str:
        return self._anonymize(
            orthanc_id=orthanc_id,
            replace_tags=replace_tags,
            keep_tags=keep_tags,
            delete_original=delete_original,
            force=force
        )

    def modify(self, orthanc_id: str, replace_tags: Any = {}, remove_tags: List[str] = [], keep_tags: List[str] = [], delete_original=True, force=False) -> str:
        return self._modify(
            orthanc_id=orthanc_id,
            replace_tags=replace_tags,
            remove_tags=remove_tags,
            keep_tags=keep_tags,
            delete_original=delete_original,
            force=force
        )

    def get_tags(self, orthanc_id: str) -> Tags:
        """
        returns tags from a "random" instance of the series, it shall contain all series tags
        """
        return self._api_client.instances.get_tags(self.get_first_instance_id(orthanc_id=orthanc_id))

    def lookup(self, dicom_id: str) -> str:
        """
        finds a series in Orthanc based on its SeriesInstanceUid

        Returns
        -------
        the instance id of the series or None if not found
        """
        return self._lookup(filter='Series', dicom_id=dicom_id)

    def download_instances(self, series_id, path) -> List[DownloadedInstance]:
        """
        downloads all instances from the series to disk
        Args:
            series_id: the series id to download
            path: the directory path where to store the downloaded files

        Returns:
            an array of DownloadedInstance
        """
        return self._api_client.instances.download_instances(self.get_instances_ids(series_id), path)
