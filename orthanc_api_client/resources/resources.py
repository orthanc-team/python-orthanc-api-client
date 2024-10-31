import datetime

import json
import logging
from typing import List, Tuple, Optional, Any
from ..exceptions import *
from ..helpers import to_dicom_date
from ..job import Job, JobStatus
import orthanc_api_client.exceptions as api_exceptions


logger = logging.getLogger(__name__)


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

    def get_json_statistics(self, orthanc_id: str):
        return self._api_client.get_json(f"{self._url_segment}/{orthanc_id}/statistics")

    def get_all_ids(self) -> List[str]:
        return self._api_client.get_json(f"{self._url_segment}/")

    def delete(self, orthanc_id: Optional[str] = None, orthanc_ids: Optional[List[str]] = None, ignore_errors: bool = False):

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

    def set_attachment(self, orthanc_id: str, attachment_name: str, content: Optional[str] = None, path: Optional[str] = None, content_type: Optional[str] = None, match_revision: Optional[str] = None):
        
        if content is None and path is not None:
            with open(path, 'rb') as f:
                content = f.read()

        headers = {}

        if content_type:
            headers['Content-Type'] = content_type

        if match_revision is not None:
            headers['If-Match'] = match_revision

        self._api_client.put(
            endpoint=f"{self._url_segment}/{orthanc_id}/attachments/{attachment_name}",
            data=content,
            headers=headers
        )

    def get_attachment(self, orthanc_id: str, attachment_name: str) -> bytes:

        content, revision = self.get_attachment_with_revision(
            orthanc_id=orthanc_id,
            attachment_name=attachment_name
        )
        return content

    def get_attachment_with_revision(self, orthanc_id: str, attachment_name: str) -> Tuple[bytes, str]:

        headers = {}

        response = self._api_client.get(
            endpoint=f"{self._url_segment}/{orthanc_id}/attachments/{attachment_name}/data",
            headers=headers
        )

        return response.content, response.headers.get('etag')

    def download_attachment(self, orthanc_id: str, attachment_name: str, path: str):
        content = self.get_attachment(orthanc_id, attachment_name)

        with open(path, 'wb') as f:
            f.write(content)

    def set_binary_metadata(self, orthanc_id: str, metadata_name: str, content: Optional[bytes] = None, path: Optional[str] = None, match_revision: Optional[str] = None):
        # sets the metadata only if the current revision matches `match_revision`
        # returns the new revision

        if content is None and path is not None:
            with open(path, 'rb') as f:
                content = f.read()

        headers = {}

        if match_revision is not None:
            headers['If-Match'] = match_revision

        self._api_client.put(
            endpoint=f"{self._url_segment}/{orthanc_id}/metadata/{metadata_name}",
            data=content,
            headers=headers
        )

    def set_string_metadata(self, orthanc_id: str, metadata_name: str, content: Optional[str] = None, path: Optional[str] = None, match_revision: Optional[str] = None):
        
        if content is None and path is not None:
            with open(path, 'rt') as f:
                content = f.read()

        self.set_binary_metadata(
            orthanc_id=orthanc_id,
            metadata_name=metadata_name,
            content=content.encode('utf-8'),
            match_revision=match_revision
        )


    def get_binary_metadata(self, orthanc_id: str, metadata_name: str, default_value: Optional[str] = None) -> bytes:

        content, revision = self.get_metadata_with_revision(
            orthanc_id=orthanc_id,
            metadata_name=metadata_name,
            default_value=default_value
        )

        return content

    def get_string_metadata(self, orthanc_id: str, metadata_name: str, default_value: Optional[str] = None) -> str:

        content, revision = self.get_binary_metadata_with_revision(
            orthanc_id=orthanc_id,
            metadata_name=metadata_name,
            default_value=default_value.encode('utf-8') if default_value is not None else None
        )

        return content.decode('utf-8') if content is not None else None

    def get_binary_metadata_with_revision(self, orthanc_id: str, metadata_name: str, default_value: Optional[bytes] = None) -> Tuple[bytes, str]:

        headers = {}

        try:
            response = self._api_client.get(
                endpoint=f"{self._url_segment}/{orthanc_id}/metadata/{metadata_name}",
                headers=headers
            )
        except ResourceNotFound:
            return default_value, None

        return response.content, response.headers.get('etag')

    def get_string_metadata_with_revision(self, orthanc_id: str, metadata_name: str, default_value: Optional[str] = None) -> Tuple[str, str]:

        content, revision = self.get_binary_metadata_with_revision(
            orthanc_id=orthanc_id,
            metadata_name=metadata_name,
            default_value=default_value.encode('utf-8') if default_value is not None else None
        )

        return content.decode('utf-8') if content is not None else None, revision

    def has_metadata(self, orthanc_id: str, metadata_name: str) -> bool:
        return self.get_metadata(orthanc_id=orthanc_id, metadata_name=metadata_name, default_value=None) is not None

    def _anonymize(self, orthanc_id: str, replace_tags={}, keep_tags=[], delete_original=True, force=False) -> str:
        """
        anonymizes the study/series and possibly deletes the original resource (the one that has not be anonymized)

        Args:
            orthanc_id: the instance id to anonymize
            replace_tags: a dico with OrthancTagsId <-> values of the tags you want to force
            keep_tags: a list of tags you want to keep unmodified
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

    def _modify(self, orthanc_id: str, replace_tags: Any = {}, remove_tags: List[str] = [], keep_tags: List[str] = [], delete_original=True, force=False) -> str:
        """
        modifies the study/series and possibly deletes the original resource (the one that has not be anonymized)

        Args:
            orthanc_id: the instance id to anonymize
            replace_tags: a dico with OrthancTagsId <-> values of the tags you want to force
            remove_tags: a list of tags you want to remove
            keep_tags: a list of tags you want to keep unmodified
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
        if keep_tags is not None and len(keep_tags) > 0:
            query['Keep'] = keep_tags

        r = self._api_client.post(
            endpoint=f"{self._url_segment}/{orthanc_id}/modify",
            json=query)

        if r.status_code == 200:
            modified_id = r.json()['ID']
            if delete_original and modified_id != orthanc_id:
                self.delete(orthanc_id)

            return modified_id

        return None  # TODO: raise exception ???

    def modify_bulk(self, orthanc_ids: List[str] = [], replace_tags: Any = {}, remove_tags: List[str] = [], keep_tags: List[str] = [], delete_original: bool = True, force: bool = False, transcode: Optional[str] = None, permissive: bool = False)  -> Tuple[List[str], List[str], List[str], List[str]]:
        """
        returns a tuple with:
        - the list of modified instances ids
        - the list of modified series ids
        - the list of modified studies ids
        - the list of modified patients ids
        """
        modified_instances_ids = []
        modified_series_ids = []
        modified_studies_ids = []
        modified_patients_ids = []

        job = self.modify_bulk_async(
            orthanc_ids=orthanc_ids,
            replace_tags=replace_tags,
            remove_tags=remove_tags,
            keep_tags=keep_tags,
            delete_original=delete_original,
            force=force,
            transcode=transcode
        )

        job.wait_completed()

        if job.info.status == JobStatus.SUCCESS and "Resources" in job.content:
            # extract the list of modified instances ids from the job content
            for r in job.content.get("Resources"):
                if r.get("Type") == "Instance":
                    modified_instances_ids.append(r.get("ID"))
                elif r.get("Type") == "Series":
                    modified_series_ids.append(r.get("ID"))
                elif r.get("Type") == "Study":
                    modified_studies_ids.append(r.get("ID"))
                elif r.get("Type") == "Patient":
                    modified_patients_ids.append(r.get("ID"))
            return modified_instances_ids, modified_series_ids, modified_studies_ids, modified_patients_ids
        else:
            raise api_exceptions.OrthancApiException(msg=f"Error while modifying bulk {self._get_level()}, job failed {json.dumps(job.info.content)}")


    def modify_bulk_async(self, orthanc_ids: List[str] = [], replace_tags: Any = {}, remove_tags: List[str] = [], keep_tags: List[str] = [], delete_original: bool = True, force: bool = False, transcode: Optional[str] = None, permissive: bool = False) -> Job:
        return self._modify_bulk_async(
            operation="modify",
            orthanc_ids=orthanc_ids,
            replace_tags=replace_tags,
            remove_tags=remove_tags,
            keep_tags=keep_tags,
            delete_original=delete_original,
            force=force,
            transcode=transcode,
            permissive=permissive)

    def _modify_bulk(self, operation: str, orthanc_ids: List[str] = [], replace_tags: Any = {}, remove_tags: List[str] = [], keep_tags: List[str] = [], delete_original: bool = True, force: bool = False, transcode: Optional[str] = None, permissive: bool = False)  -> Tuple[List[str], List[str], List[str], List[str]]:
        """
        returns a tuple with:
        - the list of modified instances ids
        - the list of modified series ids
        - the list of modified studies ids
        - the list of modified patients ids
        """
        modified_instances_ids = []
        modified_series_ids = []
        modified_studies_ids = []
        modified_patients_ids = []

        job = self._modify_bulk_async(
            operation=operation,
            orthanc_ids=orthanc_ids,
            replace_tags=replace_tags,
            remove_tags=remove_tags,
            keep_tags=keep_tags,
            delete_original=delete_original,
            force=force,
            transcode=transcode
        )

        job.wait_completed()

        if job.info.status == JobStatus.SUCCESS and "Resources" in job.content:
            # extract the list of modified instances ids from the job content
            for r in job.content.get("Resources"):
                if r.get("Type") == "Instance":
                    modified_instances_ids.append(r.get("ID"))
                elif r.get("Type") == "Series":
                    modified_series_ids.append(r.get("ID"))
                elif r.get("Type") == "Study":
                    modified_studies_ids.append(r.get("ID"))
                elif r.get("Type") == "Patient":
                    modified_patients_ids.append(r.get("ID"))
            return modified_instances_ids, modified_series_ids, modified_studies_ids, modified_patients_ids
        else:
            raise api_exceptions.OrthancApiException(msg=f"Error while {'modifying' if operation == 'modify' else 'anonymizing'} bulk {self._get_level()}, job failed {json.dumps(job.info.content)}")

    def _modify_bulk_async(self, operation: str, orthanc_ids: List[str] = [], replace_tags: Any = {}, remove_tags: List[str] = [], keep_tags: List[str] = [], delete_original: bool = True, force: bool = False, transcode: Optional[str] = None, permissive: bool = False) -> Job:
        query = {
            "Force": force,
            "Level": self._get_level(),
            "Resources": orthanc_ids,
            "Asynchronous": True,
            "Permissive": permissive
        }

        if replace_tags is not None and len(replace_tags) > 0:
            query['Replace'] = replace_tags
        if remove_tags is not None and len(remove_tags) > 0:
            query['Remove'] = remove_tags
        if keep_tags is not None and len(keep_tags) > 0:
            query['Keep'] = keep_tags
        if transcode:
            query['Transcode'] = transcode
        if delete_original:
            query['KeepSource'] = False

        r = self._api_client.post(
            endpoint=f"/tools/bulk-{operation}",
            json=query)

        if r.status_code == 200 and "ID" in r.json():
            return Job(api_client=self._api_client, orthanc_id=r.json()['ID'])
        else:
            raise HttpError(http_status_code=r.status_code, msg=f"Error in bulk-{operation}", url=r.url, request_response=r)


    def anonymize_bulk(self, orthanc_ids: List[str] = [], replace_tags: Any = {}, remove_tags: List[str] = [], keep_tags: List[str] = [], delete_original: bool = False, force: bool = False, transcode: Optional[str] = None, permissive: bool = False)  -> Tuple[List[str], List[str], List[str], List[str]]:
        """
        returns a tuple with:
        - the list of anonymized instances ids
        - the list of anonymized series ids
        - the list of anonymized studies ids
        - the list of anonymized patients ids
        """
        return self._modify_bulk(
            operation="anonymize",
            orthanc_ids=orthanc_ids,
            replace_tags=replace_tags,
            remove_tags=remove_tags,
            keep_tags=keep_tags,
            delete_original=delete_original,
            force=force,
            transcode=transcode,
            permissive=permissive)

    def anonymize_bulk_async(self, orthanc_ids: List[str] = [], replace_tags: Any = {}, remove_tags: List[str] = [], keep_tags: List[str] = [], delete_original: bool = False, force: bool = False, transcode: Optional[str] = None, permissive: bool = False) -> Job:
        return self._modify_bulk_async(
            operation="anonymize",
            orthanc_ids=orthanc_ids,
            replace_tags=replace_tags,
            remove_tags=remove_tags,
            keep_tags=keep_tags,
            delete_original=delete_original,
            force=force,
            transcode=transcode,
            permissive=permissive)

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

    def get_labels(self, orthanc_id: str) -> List[str]:
        """
        Gets all the labels of this resource

        Returns:
            A list containing oll the labels of this resource
        """
        return self._api_client.get_json(f"{self._url_segment}/{orthanc_id}/labels")

    def add_label(self, orthanc_id: str, label: str):
        """
        Add the label to the resource

        Args:
            orthanc_id: resource to add the label to
            label: the label to add to the resource
        """

        self._api_client.put(f"{self._url_segment}/{orthanc_id}/labels/{label}")

    def add_labels(self, orthanc_id: str, labels: List[str]):
        """
        Add the labels to the resource

        Args:
            orthanc_id: resource to add the labels to
            labels: the list of labels to add to the resource
        """
        for label in labels:
            self.add_label(orthanc_id, label)

    def delete_label(self, orthanc_id: str, label: str):
        """
        Delete the label from the resource

        Args:
            orthanc_id: resource to remove the label from
            label: the label to remove from the resource
        """

        self._api_client.delete(f"{self._url_segment}/{orthanc_id}/labels/{label}")

    def delete_labels(self, orthanc_id: str, labels: List[str]):
        """
        Delete the labels from the resource

        Args:
            orthanc_id: resource to remove the labels from
            labels: the labels to remove from the resource
        """
        for label in labels:
            self.delete_label(orthanc_id, label)

    def exists(self, orthanc_id: str) -> bool:
        try:
            self._api_client.get(
                endpoint=f"{self._url_segment}/{orthanc_id}"
            )
            return True
        except ResourceNotFound:
            return False

    def download_archive(self, orthanc_id: str, path: str):
        file_content = self._api_client.get_binary(f"{self._url_segment}/{orthanc_id}/archive")
        with open(path, 'wb') as f:
            f.write(file_content)

    def download_media(self, orthanc_id: str, path: str):
        file_content = self._api_client.get_binary(f"{self._url_segment}/{orthanc_id}/media")
        with open(path, 'wb') as f:
            f.write(file_content)
