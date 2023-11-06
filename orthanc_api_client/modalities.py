import typing
from typing import List, Union, Optional
from .tags import SimplifiedTags
from .study import Study
from .job import Job
from .exceptions import ResourceNotFound

from .exceptions import *


class RemoteModalityStudy:

    """
    Represents a study on a remote modality.  This is populated with the results of a C-Find request on that modality

    You can retrieve the study by calling:
    orthanc.modalities.retrieve_study(remote_study.remote_modality_id, remote_study.dicom_id)
    """

    def __init__(self):
        self.dicom_id = None                    # the StudyInstanceUID dicom tag
        self.remote_modality_id = None          # the alias of the modality where the study is
        self.tags = None                        # the tags that have been retrieved (depends on the query used to find it)


class RemoteModalitySeries:

    """
    Represents a series on a remote modality.  This is populated with the results of a C-Find request on that modality
    """

    def __init__(self):
        self.dicom_id = None                    # the SeriesInstanceUID dicom tag
        self.remote_modality_id = None          # the alias of the modality where the study is
        self.tags = None                        # the tags that have been retrieved (depends on the query used to find it)


class RemoteModalityInstance:

    """
    Represents an instance on a remote modality.  This is populated with the results of a C-Find request on that modality
    """

    def __init__(self):
        self.dicom_id = None                    # the SOPInstanceUID dicom tag
        self.remote_modality_id = None          # the alias of the modality where the study is
        self.tags = None                        # the tags that have been retrieved (depends on the query used to find it)


class QueryResult:

    def __init__(self):
        self.tags = None
        self.retrieve_url = None


class DicomModalities:

    def __init__(self, api_client: 'OrthancApiClient'):
        self._api_client = api_client
        self._url_segment = 'modalities'


    def find_worklist(self, modality: str, query = {}):
        r = self._api_client.post(
            endpoint=f"{self._url_segment}/{modality}/find-worklist",
            json=query
        )

        if r.status_code == 200:
            return r.json()

    def store(self, target_modality: str, resources_ids: Union[List[str], str], timeout: Optional[float] = None):
        """alias for send"""
        return self.send(target_modality=target_modality, resources_ids=resources_ids, timeout=timeout)

    def send_async(self, target_modality: str, resources_ids: Union[List[str], str], local_aet: str = None) -> Job:
        """sends a list of resources to a remote DICOM modality

        Returns
        -------
        the created job
        """

        if isinstance(resources_ids, str):
            resources_ids = [resources_ids]

        payload = {
            "Resources": resources_ids,
            "Synchronous": False
        }
        if local_aet is not None:
            payload.update({"LocalAet": local_aet})

        r = self._api_client.post(
            endpoint=f"{self._url_segment}/{target_modality}/store",
            json=payload
        )

        return Job(api_client=self._api_client, orthanc_id=r.json()['ID'])

    def send(self, target_modality: str, resources_ids: Union[List[str], str], timeout: Optional[float] = None, local_aet: str = None):
        """sends a list of resources to a remote DICOM modality
        The transfer is synchronous

        Returns
        -------
        Nothing, will raise if failing
        """

        if isinstance(resources_ids, str):
            resources_ids = [resources_ids]

        payload = {
            "Synchronous": True,
            "Resources": resources_ids
        }

        if timeout is not None:
            payload["Timeout"] = int(timeout+0.5)

        if local_aet is not None:
            payload.update({"LocalAet": local_aet})

        self._api_client.post(
            endpoint=f"{self._url_segment}/{target_modality}/store",
            json=payload)

    def retrieve_study(self, from_modality: str, dicom_id: str) -> str:
        """
        retrieves a study from a remote modality (C-Move)

        this call is synchronous.  It completes once the C-Move is complete.

        :param from_modality: the modality alias configured in orthanc
        :param dicom_id: the StudyInstanceUid of the study to retrieve

        Returns: the study orthanc_id of the study once it has been retrieved in orthanc
        """

        # move the study from the remote modality to this orthanc
        self.move_study(
            from_modality=from_modality,
            dicom_id=dicom_id
        )

        # this request has no real response '{}' if it succeeds
        return self._api_client.studies.lookup(dicom_id)

    def move_study(self, from_modality: str, dicom_id: str, to_modality_aet: str = None):
        """
        moves a study from a remote modality (C-Move) to a target modality (AET)

        this call is synchronous.  It completes once the C-Move is complete.

        :param from_modality: the modality alias configured in orthanc
        :param dicom_id: the StudyInstanceUid of the study to move
        :param to_modality_aet: the AET of the target modality
        """
        self._move(
            level="Study",
            resource={
                "StudyInstanceUID": dicom_id
            },
            from_modality=from_modality,
            to_modality_aet=to_modality_aet
        )

    def move_series(self, from_modality: str, dicom_id: str, study_dicom_id: str, to_modality_aet: str = None):
        """
        moves a series from a remote modality (C-Move) to a target modality (AET)

        this call is synchronous.  It completes once the C-Move is complete.

        :param from_modality: the modality alias configured in orthanc
        :param dicom_id: the SeriesInstanceUID of the series to move
        :param study_dicom_id: the StudyInstanceUID of the parent study
        :param to_modality_aet: the AET of the target modality
        """
        self._move(
            level="Series",
            resource={
                "SeriesInstanceUID": dicom_id,
                "StudyInstanceUID": study_dicom_id
            },
            from_modality=from_modality,
            to_modality_aet=to_modality_aet
        )

    def move_instance(self, from_modality: str, dicom_id: str, series_dicom_id: str, study_dicom_id: str, to_modality_aet: str = None):
        """
        moves an instance from a remote modality (C-Move) to a target modality (AET)

        this call is synchronous.  It completes once the C-Move is complete.

        :param from_modality: the modality alias configured in orthanc
        :param dicom_id: the SOPInstanceUid of the instance to move
        :param series_dicom_id: the SeriesInstanceUID of the parent series
        :param study_dicom_id: the StudyInstanceUID of the parent study
        :param to_modality_aet: the AET of the target modality
        """
        self._move(
            level="Instance",
            resource={
                "SOPInstanceUID": dicom_id,
                "SeriesInstanceUID": series_dicom_id,
                "StudyInstanceUID": study_dicom_id
            },
            from_modality=from_modality,
            to_modality_aet=to_modality_aet
        )

    def _move(self, level: str, resource: object, from_modality: str, to_modality_aet: str = None):
        """
        moves a study from a remote modality (C-Move) to a target modality (AET)

        this call is synchronous.  It completes once the C-Move is complete.

        :param from_modality: the modality alias configured in orthanc
        :param to_modality_aet: the AET of the target modality
        """

        payload = {
            'Level': level,
            'Resources': [resource]
        }

        if to_modality_aet:
            payload['TargetAet'] = to_modality_aet

        self._api_client.post(
            endpoint=f"{self._url_segment}/{from_modality}/move",
            json=payload)


    def query_studies(self, from_modality: str, query: object) -> typing.List[RemoteModalityStudy]:
        """
        queries a remote modality for studies

        :param from_modality: the modality alias configured in orthanc
        :param query: DICOM queries; i.e: {PatientName:'TOTO*', StudyDate:'20150503-'}
        """

        payload = {
            'Level': 'Studies',
            'Query': query
        }

        results = self._query(from_modality, payload)

        remote_studies = []
        for result in results:
            remote_study = RemoteModalityStudy()
            remote_study.dicom_id = result.tags.get('StudyInstanceUID')
            remote_study.tags = result.tags
            remote_study.remote_modality_id = from_modality

            remote_studies.append(remote_study)

        return remote_studies

    def query_series(self, from_modality: str, query: object) -> typing.List[RemoteModalitySeries]:
        """
        queries a remote modality for series

        :param from_modality: the modality alias configured in orthanc
        :param query: DICOM queries; i.e: {PatientName:'TOTO*', StudyDate:'20150503-'}
        """

        payload = {
            'Level': 'Series',
            'Query': query
        }

        results = self._query(from_modality, payload)

        remote_series = []
        for result in results:
            remote_serie = RemoteModalitySeries()
            remote_serie.dicom_id = result.tags.get('SeriesInstanceUID')
            remote_serie.tags = result.tags
            remote_serie.remote_modality_id = from_modality

            remote_series.append(remote_serie)

        return remote_series

    def query_instances(self, from_modality: str, query: object) -> typing.List[RemoteModalityInstance]:
        """
        queries a remote modality for instances

        :param from_modality: the modality alias configured in orthanc
        :param query: DICOM queries; i.e: {PatientName:'TOTO*', StudyDate:'20150503-'}
        """

        payload = {
            'Level': 'Instance',
            'Query': query
        }

        results = self._query(from_modality, payload)

        remote_instances = []
        for result in results:
            remote_instance = RemoteModalityInstance()
            remote_instance.dicom_id = result.tags.get('SOPInstanceUID')
            remote_instance.tags = result.tags
            remote_instance.remote_modality_id = from_modality

            remote_instances.append(remote_instance)

        return remote_instances

    def _query(self, from_modality, payload) -> typing.List[QueryResult]:

        query = self._api_client.post(
            endpoint=f"{self._url_segment}/{from_modality}/query",
            json=payload)

        query_id = query.json()['ID']

        results = []

        answers = self._api_client.get(endpoint = f"queries/{query_id}/answers")

        for answer_id in answers.json():
            result = QueryResult()
            result.tags = SimplifiedTags(self._api_client.get(f"queries/{query_id}/answers/{answer_id}/content?simplify").json())
            result.retrieve_url = f"queries/{query_id}/answers/{answer_id}/retrieve"
            results.append(result)

        return results

    def delete(self, modality: str):
        query = self._api_client.delete(
            endpoint=f"{self._url_segment}/{modality}")

    def configure(self, modality: str, configuration: dict):

        query = self._api_client.put(
            endpoint=f"{self._url_segment}/{modality}",
            json=configuration
        )

    def get_configuration(self, modality: str) -> dict:
        all_modalities = self._api_client.get_json(
            endpoint=f"{self._url_segment}?expand"
        )

        if modality in all_modalities:
            return all_modalities[modality]
        else:
            raise ResourceNotFound(msg=f"The modality {modality} was not found")

    def get_all_ids(self) -> List[str]:
        return self._api_client.get_json(
            endpoint=f"{self._url_segment}"
        )

    def get_id_from_aet(self, aet: str) -> str:
        all_modalities = self._api_client.get_json(
            endpoint=f"{self._url_segment}?expand"
        )

        for (alias, values) in all_modalities.items():
            if values["AET"] == aet:
                return alias
        else:
            raise ResourceNotFound(msg=f"No modality found with AET '{aet}'")
