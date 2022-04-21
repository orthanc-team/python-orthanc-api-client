import typing
from typing import List, Union
from .tags import SimplifiedTags
from .study import Study

from .exceptions import *


class RemoteModalityStudy:

    """
    Represents a study on a remote modality.  This is populated with the results of a C-Find request on that modality

    You can retrieve the study by calling:
    orthanc.modalities.retrieve_study(remoteStudy.remote_mModality_id, remote_study.dicom_id)
    """

    def __init__(self):
        self.dicom_id = None                    # the StudyInstanceUID dicom tag
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
            relative_url=f"{self._url_segment}/{modality}/find-worklist",
            json=query
        )

        if r.status_code == 200:
            return r.json()

    def store(self, modality: str, resources_ids: Union[List[str], str], synchronous: bool = True):
        """alias for send"""
        return self.send(modality=modality, resources_ids=resources_ids, synchronous=synchronous)

    def send(self, modality: str, resources_ids: Union[List[str], str], synchronous: bool = True):
        """sends a list of resources to a remote DICOM modality

        Returns
        -------
        Nothing, will raise if failing
        """

        if isinstance(resources_ids, str):
            resources_ids = [resources_ids]

        r = self._api_client.post(
            relative_url=f"{self._url_segment}/{modality}/store",
            json={
                "Resources": resources_ids,
                "Synchronous": synchronous
            })

        return None

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
        :param dicom_id: the StudyInstanceUid of the study to retrieve
        :param to_modality_aet: the AET of the target modality
        """

        payload = {
            'Level': 'Study',
            'Resources': [{'StudyInstanceUID': dicom_id}]
        }

        if to_modality_aet:
            payload['TargetAet'] = to_modality_aet

        self._api_client.post(
            relative_url=f"{self._url_segment}/{from_modality}/move",
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

    def _query(self, from_modality, payload) -> typing.List[QueryResult]:

        query = self._api_client.post(
            relative_url=f"{self._url_segment}/{from_modality}/query",
            json=payload)

        query_id = query.json()['ID']

        results = []

        answers = self._api_client.get(relative_url = f"queries/{query_id}/answers")

        for answer_id in answers.json():
            result = QueryResult()
            result.tags = SimplifiedTags(self._api_client.get(f"queries/{query_id}/answers/{answer_id}/content?simplify").json())
            result.retrieve_url = f"queries/{query_id}/answers/{answer_id}/retrieve"
            results.append(result)

        return results
