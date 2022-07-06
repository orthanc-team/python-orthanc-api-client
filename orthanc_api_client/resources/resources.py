import datetime

import requests
import logging
from typing import List, Tuple
from ..exceptions import *
from ..helpers import to_dicom_date


logger = logging.getLogger('api-client')


class Resources:

    def __init__(self, api_client: 'OrthancApiClient', url_segment: str):
        self._url_segment = url_segment
        self._api_client = api_client

    def _get_level(self):
        if self._url_segment == "studies":
            return "Study"
        elif self._url_segment == "series":
            return "Series"
        elif self._url_segment == "instances":
            return "Instance"
        elif self._url_segment == "patients":
            return "Patient"

    def get_json(self, orthanc_id: str):
        return self._api_client.get_json(f"{self._url_segment}/{orthanc_id}")

    def get_all_ids(self) -> List[str]:
        return self._api_client.get_json(f"{self._url_segment}/")

    def delete(self, orthanc_id: str = None, orthanc_ids: List[str] = None, ignore_errors: bool = False):

        if orthanc_ids:
            for oi in orthanc_ids:
                self.delete(orthanc_id=oi, ignore_errors=ignore_errors)

        if orthanc_id:
            logger.debug(f"deleting {self._url_segment} {orthanc_id}")
            try:
                self._api_client.delete(f"{self._url_segment}/{orthanc_id}")
            except ResourceNotFound as ex:
                if not ignore_errors:
                    raise ex

    def delete_all(self, ignore_errors: bool = False) -> List[str]:
        all_ids = self.get_all_ids()
        deleted_ids = []

        for orthanc_id in all_ids:
            self.delete(orthanc_id, ignore_errors=ignore_errors)
            deleted_ids.append(orthanc_id)
        
        return deleted_ids

    def set_attachment(self, orthanc_id, attachment_name, content=None, path=None, content_type=None, match_revision=None):
        
        if content is None and path is not None:
            with open(path, 'rb') as f:
                content = f.read()

        headers = {}

        if content_type:
            headers['Content-Type'] = content_type

        if match_revision:
            headers['If-Match'] = match_revision

        self._api_client.put(
            endpoint=f"{self._url_segment}/{orthanc_id}/attachments/{attachment_name}",
            data=content,
            headers=headers
        )

    def get_attachment(self, orthanc_id, attachment_name) -> bytes:

        content, revision = self.get_attachment_with_revision(
            orthanc_id=orthanc_id,
            attachment_name=attachment_name
        )
        return content

    def get_attachment_with_revision(self, orthanc_id, attachment_name) -> Tuple[bytes, str]:

        headers = {}

        response = self._api_client.get(
            endpoint=f"{self._url_segment}/{orthanc_id}/attachments/{attachment_name}/data",
            headers=headers
        )

        return response.content, response.headers.get('etag')

    def download_attachment(self, orthanc_id, attachment_name, path):
        content = self.get_attachment(orthanc_id, attachment_name)

        with open(path, 'wb') as f:
            f.write(content)

    def set_metadata(self, orthanc_id, metadata_name, content=None, path=None, match_revision=None):
        
        if content is None and path is not None:
            with open(path, 'rb') as f:
                content = f.read()

        headers = {}

        if match_revision:
            headers['If-Match'] = match_revision

        self._api_client.put(
            endpoint=f"{self._url_segment}/{orthanc_id}/metadata/{metadata_name}",
            data=content,
            headers=headers
        )

    def get_metadata(self, orthanc_id, metadata_name, default_value=None) -> bytes:

        content, revision = self.get_metadata_with_revision(
            orthanc_id=orthanc_id,
            metadata_name=metadata_name,
            default_value=default_value
        )

        return content

    def get_metadata_with_revision(self, orthanc_id, metadata_name, default_value=None) -> Tuple[bytes, str]:

        headers = {}

        try:
            response = self._api_client.get(
                endpoint=f"{self._url_segment}/{orthanc_id}/metadata/{metadata_name}",
                headers=headers
            )
        except ResourceNotFound:
            return default_value, None

        return response.content, response.headers.get('etag')


    def _anonymize(self, orthanc_id: str, replace_tags={}, keep_tags=[], delete_original=True, force=False) -> str:
        """
        anonymizes the study/series and possibly deletes the original resource (the one that has not be anonymized)

        Args:
            orthanc_id: the instance id to anonymize
            replace_tags: a dico with OrthancTagsId <-> values of the tags you want to force
            keep_tags: a list of the tags you want to keep the original values
            delete_original: True to delete the original study (the one that has not been anonymized)
            force: some tags like "PatientID" requires this flag set to True to confirm that you understand the risks
        Returns:
            the id of the new anonymized study/series
        """

        query = {
            "Force": force
        }
        if replace_tags is not None and len(replace_tags) > 0:
            query['Replace'] = replace_tags
        if keep_tags is not None and len(keep_tags) > 0:
            query['Keep'] = keep_tags

        r = self._api_client.post(
            endpoint=f"{self._url_segment}/{orthanc_id}/anonymize",
            json=query)

        if r.status_code == 200:
            anonymized_id = r.json()['ID']
            if delete_original and anonymized_id != orthanc_id:
                self.delete(orthanc_id)

            return anonymized_id

        return None  # TODO: raise exception ???

    def _modify(self, orthanc_id: str, replace_tags={}, remove_tags=[], delete_original=True, force=False) -> str:
        """
        modifies the study/series and possibly deletes the original resource (the one that has not be anonymized)

        Args:
            orthanc_id: the instance id to anonymize
            replace_tags: a dico with OrthancTagsId <-> values of the tags you want to force
            remove_tags: a list of the tags you want to remove from the original values
            delete_original: True to delete the original study (the one that has not been anonymized)
            force: some tags like "PatientID" requires this flag set to True to confirm that you understand the risks
        Returns:
            the id of the new anonymized study/series
        """

        query = {
            "Force": force
        }
        if replace_tags is not None and len(replace_tags) > 0:
            query['Replace'] = replace_tags
        if remove_tags is not None and len(remove_tags) > 0:
            query['Remove'] = remove_tags

        r = self._api_client.post(
            endpoint=f"{self._url_segment}/{orthanc_id}/modify",
            json=query)

        if r.status_code == 200:
            modified_id = r.json()['ID']
            if delete_original and modified_id != orthanc_id:
                self.delete(orthanc_id)

            return modified_id

        return None  # TODO: raise exception ???

    def print_daily_stats(self, from_date: datetime.date = None, to_date: datetime.date = None):
        if self._url_segment == "patients":
            raise NotImplementedError("Print daily stats is not implemented for Patient level")

        if to_date is None:
            to_date = datetime.date.today()

        if from_date is None:
            from_date = to_date - datetime.timedelta(days=7)

        level = self._get_level()
        system = self._api_client.get_system()

        print(f"Daily {level} stats for " + system["DicomAet"] + " - " + system["Name"])
        print("---------------------------------------")

        current_date = from_date

        while current_date <= to_date:

            payload = {
                "Level": level,
                "Query": {
                    "StudyDate": to_dicom_date(current_date)
                },
                "Expand": False,
                "CaseSensitive": False
            }

            r = self._api_client.post(
                endpoint=f"tools/find",
                json=payload)

            print(f"{current_date} - " + str(len(r.json())))
            current_date += datetime.timedelta(days=1)

    def _lookup(self, filter: str, dicom_id: str) -> str:
        """
        finds a resource in Orthanc based on its dicom id

        Returns
        -------
        the instance id of the study or None if not found
        """
        resource_ids = self._api_client.lookup(needle=dicom_id, filter=filter)
        if len(resource_ids) == 1:
            return resource_ids[0]

        if len(resource_ids) > 1:
            raise TooManyResourcesFound()
        return None
