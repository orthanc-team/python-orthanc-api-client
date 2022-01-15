from .resources import Resources
from .tags import Tags
from .exceptions import *


class Studies(Resources):

    def __init__(self, api_client: 'OrthancApiClient'):
        super().__init__(api_client=api_client, url_segment='studies')

    def find(self, StudyInstanceUID: str) -> str:
        """
        finds a study in Orthanc based on its StudyInstanceUid

        Returns
        -------
        the instance id of the study or None if not found
        """
        study_ids = self._api_client.lookup(needle=StudyInstanceUID, filter='Study')
        if len(study_ids) == 1:
            return study_ids[0]

        if len(study_ids) > 1:
            raise TooManyResourcesFound()        
        return None

    def anonymize(self, orthanc_id: str, replace_tags={}, keep_tags=[], delete_original=True, force=False) -> str:
        """
        anonymizes the study and possibly deletes the original study (the one that has not be anonymized)

        Args:
            orthanc_id: the instance id to anonymize
            replace_tags: a dico with OrthancTagsId <-> values of the tags you want to force
            keep_tags: a list of the tags you want to keep the original values
            delete_original: True to delete the original study (the one that has not been anonymized)
            force: some tags like "PatientID" requires this flag set to True to confirm that you understand the risks
        Returns:
            the id of the new anonymized study
        """

        query = {
            "Force": force
        }
        if replace_tags is not None and len(replace_tags) > 0:
            query['Replace'] = replace_tags
        if keep_tags is not None and len(keep_tags) > 0:
            query['Keep'] = keep_tags

        r = self._api_client.post(
            relative_url=f"/studies/{orthanc_id}/anonymize",
            json=query)

        if r.status_code == 200 and delete_original:
            self.delete(orthanc_id)

        return r.json()['ID']

    def get_tags(self, orthanc_id: str) -> Tags:
        """
        returns tags from the study and patient modules only
        """
        study_module_json_tags = self._api_client.get_json(f"/{self._url_segment}/{orthanc_id}/module")
        study_tags = Tags(study_module_json_tags)

        patient_module_json_tags = self._api_client.get_json(f"/{self._url_segment}/{orthanc_id}/module-patient")
        patient_tags = Tags(patient_module_json_tags)
        study_tags.append(patient_tags)

        return study_tags
